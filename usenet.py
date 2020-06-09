import argparse
import glob
import json
import os
import re
import zipfile as zpf
from io import FileIO
from itertools import product

import dataset
import matplotlib.pyplot as plt
import ndlib.models.CompositeModel as CompMod
import ndlib.models.ModelConfig as MoCon
import networkx as nx
import numpy as np
import pandas as pd
from dateutil.parser import ParserError
from dateutil.parser import parse as dateparse
from ndlib.models.compartments import NodeStochastic
from ndlib.models.compartments import NodeThreshold
from ndlib.utils import multi_runs
from scipy.optimize import minimize
from tqdm import tqdm

failures = []


def usenet_reader(zp: FileIO):
    """
    An iterator that takes a ZipFile or other file-like object and returns the usenet posts in order according to RFC
    1036 and later NetNews formats.
    :param io.FileIO zp: a file that contains a usenet or netnews mailbox
    :return str: A post, iteratively
    """
    outfile = b''
    line = True
    spot = zp.tell()
    while line:
        line = zp.readline()
        if re.match(b'From [\\d-]+$', line):
            if outfile != b'':
                yield str(outfile), zp.tell() - spot
                spot = zp.tell()
            outfile = b''

        outfile += line


class Post:
    def __init__(self, data):
        global failures
        raw = data.replace('\\t', '').replace('\\r', '').split('\\n')

        self.source = self.source_finder(raw)
        self.date = self.date_finder(raw)
        self.newsgroups = self.ngroups_finder(raw)
        self.subject = self.subject_finder(raw)
        self.message_id = self.mid_finder(raw)
        self.body = self.body_finder(raw)

    @staticmethod
    def firstmatch(pattern: re.Pattern, data):
        for item in data:
            if pattern.match(item):
                return item
        return ''

    @staticmethod
    def body_finder(raw):
        def first_blank(strlist):
            for i, s in enumerate(strlist):
                if len(s) == 0:
                    return i

        t = first_blank(raw)
        return '\n'.join(raw[t:])

    @staticmethod
    def source_finder(raw):
        s = Post.firstmatch(re.compile(r'[fF]rom: '), raw)[6:]
        try:
            return re.findall('\\S+@\\S+', s)[0].strip('<>')
        except IndexError:
            return ''

    @staticmethod
    def date_finder(raw):
        d = Post.firstmatch(re.compile(r'[Dd]ate: '), raw)[6:]
        d = d.replace('\\t', '')
        try:
            return dateparse(d, ignoretz=True)
        except ParserError:
            try:
                return dateparse(re.findall('.+ [\\d:]+', d)[0])
            except (ParserError, IndexError):
                return None

    @staticmethod
    def ngroups_finder(raw):
        ng = Post.firstmatch(re.compile(r'[Nn]ewsgroups: '), raw)[12:].split(',')
        ng = [n.strip() for n in ng if n.strip() != '']
        return tuple(ng)

    @staticmethod
    def subject_finder(raw):
        s = Post.firstmatch(re.compile(r'[Ss]ubject: '), raw)[9:]
        return s

    @staticmethod
    def mid_finder(raw):
        mid = Post.firstmatch(re.compile(r'[Mm]essage-[Ii][Dd]: '), raw)[12:]
        return mid

    def __repr__(self):
        return f'Post ID: {self.message_id}'

    def __str__(self):
        return f'Post from: {self.source} with subject: {self.subject}'

    def __eq__(self, other):
        try:
            return self.message_id == other.message_id
        except AttributeError:
            raise NotImplemented

    def __hash__(self):
        return hash(self.message_id)

    def save(self, loc='../Data/games2.db'):

        db = dataset.connect(f'sqlite:///{loc}', reflect_metadata=False)
        post_table = db['posts']
        newsgroup_table = db['posts']
        data_dump = {'source': self.source,
                     'date': self.date,
                     'subject': self.subject,
                     'message_id': self.message_id,
                     'body': self.body,
                     'newsgroups': json.dumps(self.newsgroups)}
        post_table.upsert(data_dump, ['message_id'])
        news_data = {group.replace('.', '_').replace('-', '$'): 1 for group in self.newsgroups if group != ''}
        news_data['message_id'] = self.message_id
        newsgroup_table.upsert(news_data, ['message_id'])


class Newsgroup(dict):
    def __init__(self, name, posts=(), quiet=False, loc='../Data/games2.db'):
        super().__init__(self)
        self.loc = loc

        self.name = name
        self.load(quiet=quiet)
        for post in posts:
            self[post.message_id] = post

    def save(self):
        db = dataset.connect(f'sqlite:///{self.loc}', reflect_metadata=False)
        if not os.path.exists(self.loc) or len(db['posts']) == 0:
            seed = self.pop(list(self.keys())[0])
            seed.save()
        disk_mids = {d['message_id'] for d in db.query('SELECT message_id FROM posts')}
        mem_mids = {post.message_id for post in self.values()}
        new_mids = mem_mids - disk_mids
        tar_posts = []
        pbar = tqdm(new_mids)
        pbar.set_description(f'Processing save data for {self.name}')
        for mid in pbar:
            post = self[mid]
            data_dump = {'source': post.source,
                         'date': post.date,
                         'subject': post.subject,
                         'message_id': post.message_id,
                         'body': post.body,
                         'newsgroups': json.dumps(post.newsgroups)}

            tar_posts.append(data_dump)
        print(f'Saving {self.name}...')
        print(f'{len(new_mids)} new records found')
        db['posts'].insert_many(tar_posts, chunk_size=100000)

    def load(self, quiet=False):
        if not quiet:
            print(f'Loading {self.name}...')

        db = dataset.connect(f'sqlite:///{self.loc}', reflect_metadata=False)

        if db['posts']:
            for row in db.query(f"SELECT * FROM posts WHERE newsgroups LIKE '%{self.name}%'"):
                row.pop('id')
                new_post = Post.__new__(Post)
                for colname in row:
                    if colname == 'newsgroups':
                        new_post.newsgroups = json.loads(row['newsgroups'])
                    else:
                        new_post.__dict__[colname] = row[colname]
                self[row['message_id']] = new_post

    @classmethod
    def from_mbox(cls, file_name, rm=False, save=True, quiet=True):
        name = file_name.split('/')[-1][:-9]
        hierarchy = name.split('.')[0]
        if not os.path.exists(f'../Data/{hierarchy}'):
            os.mkdir(f'../Data/{hierarchy}')
        self = cls(name, quiet=quiet)
        with zpf.ZipFile(file_name, 'r') as zp:
            raw = zp.open(f'{name}.mbox')
            raw.seek(0, 2)
            size = raw.tell()
            raw.seek(0, 0)

        with tqdm(usenet_reader(raw), total=size) as pbar:
            pbar.set_description(f'Loading {name}...')
            for post, line in usenet_reader(raw):
                post = Post(post)
                self[post.message_id] = post
                pbar.update(line)
        if save:
            self.save()

        if rm:
            os.remove(file_name)

        return self

    @classmethod
    def from_hierarchy_mboxes(cls, hierarchy, rm=False, save=True):
        toplevel = hierarchy.split('.')[0]
        big_group = cls(hierarchy, quiet=True)
        all_boards = glob.glob(f'../Data/usenet-{toplevel}/{hierarchy}*')
        for group in all_boards:
            big_group.update(**Newsgroup.from_mbox(group, rm=rm, save=False))

        if save:
            big_group.save()

        return big_group


def process_newsgroups(*args):
    for arg in args:
        toplevel = arg.split('.')[0]
        all_boards = glob.glob(f'../Data/usenet-{toplevel}/{arg}*')
        for group in all_boards:
            Newsgroup.from_mbox(group, rm=True, save=True)


def distance(x, y):
    x = x.split('.')
    y = y.split('.')
    x = np.array([None] + x)
    y = np.array([None] + y)
    it = [x, y]
    lind = max(it, key=len)
    lind = it.index(lind)
    i = len(it[lind]) - 1
    for level in it[lind][::-1]:
        if level in it[not lind]:
            j = np.where(it[not lind] == level)[0]
            try:
                if it[lind][i - 1] == it[not lind][j - 1]:
                    break
            except IndexError:
                i = 0
                break
        if level:
            i -= 1
    return len(it[lind][i + 1:]) + len(it[not lind][i + 1:])


def post_distance(x, y, agg=np.mean):
    combos = product(x, y)
    return agg([distance(*p) for p in combos])


def distance_time_plot(post_set, agg=np.mean):
    postime = sorted(post_set, key=lambda x: x['date'])
    source = postime[0]
    dists = []
    times = []
    for post in postime:
        dists.append(post_distance(json.loads(source['newsgroups']), json.loads(post['newsgroups']), agg=agg))
        times.append(post['date'])
    plt.scatter(times, dists)
    return times, dists


# The following is code taken from Jon Clindaniel at UChicago, and was given to me in a class I took from him.


# Function simulates model given parameters and gives us y_forecasted below (mean trend)
def simulate_net_diffusion(frac_infected=0.01, threshold=0.18, profile=0.00001, p_removal=0.017, num_exec=10,
                           num_iter=100, nproc=8):

    g = nx.erdos_renyi_graph(1000, 0.1)

    # Composite Model instantiation
    sir_th_model = CompMod.CompositeModel(g)

    # Model statuses
    sir_th_model.add_status("Susceptible")
    sir_th_model.add_status("Infected")
    sir_th_model.add_status("Removed")

    # Compartment definition
    c1 = NodeThreshold(threshold=None, triggering_status="Infected")
    c2 = NodeStochastic(p_removal)

    # Rule definition
    sir_th_model.add_rule("Susceptible", "Infected", c1)
    sir_th_model.add_rule("Infected", "Removed", c2)

    # Model initial status configuration
    config = MoCon.Configuration()
    config.add_model_parameter('fraction_infected', frac_infected)

    # Setting nodes parameters
    for i in g.nodes():
        config.add_node_configuration("threshold", i, threshold)
        config.add_node_configuration("profile", i, profile)

    # Simulation execution
    sir_th_model.set_initial_status(config)
    trends = multi_runs(sir_th_model, execution_number=num_exec, iteration_number=num_iter, nprocesses=nproc)

    df_infected = pd.DataFrame([execution['trends']['node_count'][1] for execution in trends])

    # Normalize each run:
    df_infected = df_infected.apply(lambda x: x / x.max(), axis=1)
    df_infected = pd.melt(df_infected, var_name='Execution', value_name='Infected')

    # Normalize (mean) values so that they are consistent with Google Trends Data for comparison:
    y_forecasted = df_infected.groupby('Execution').mean() * 100

    return y_forecasted


# Function returns results from all simulated runs for plotting 95% Confidence Intervals of Predictions
def full_simulate_net_diffusion(frac_infected=0.01, threshold=0.038, profile=0.0000105, p_removal=0.22, num_exec=20,
                                num_iter=32, nproc=8):
    # Network generation
    g = nx.erdos_renyi_graph(1000, 0.1)

    # Composite Model instantiation
    sir_th_model = CompMod.CompositeModel(g)

    # Model statuses
    sir_th_model.add_status("Susceptible")
    sir_th_model.add_status("Infected")
    sir_th_model.add_status("Removed")

    # Compartment definition
    c1 = NodeThreshold(threshold=None, triggering_status="Infected")
    c2 = NodeStochastic(p_removal)

    # Rule definition
    sir_th_model.add_rule("Susceptible", "Infected", c1)
    sir_th_model.add_rule("Infected", "Removed", c2)

    # Model initial status configuration, assume 1% of population is infected
    config = MoCon.Configuration()
    config.add_model_parameter('fraction_infected', frac_infected)

    # Setting nodes parameters
    for i in g.nodes():
        config.add_node_configuration("threshold", i, threshold)
        config.add_node_configuration("profile", i, profile)

    # Simulation execution
    sir_th_model.set_initial_status(config)
    trends = multi_runs(sir_th_model, execution_number=num_exec, iteration_number=num_iter, nprocesses=nproc)

    # Convert into a dataframe that lists each number of infected nodes by iteration number (to make average
    # calculation)
    df_infected = pd.DataFrame([execution['trends']['node_count'][1] for execution in trends])

    # Normalize each run, so that they are consistent with Google Trends Data for comparison:
    df_infected = df_infected.apply(lambda x: x / x.max(), axis=1)
    df_infected = pd.melt(df_infected, var_name='Execution', value_name='Infected')
    df_infected['Infected'] *= 100

    return df_infected


def mse(params, y_actual, time_steps):
    # Returns Mean Squared Error of the forecasted values, in comparison to actual values, for given parameters
    y_forecasted = \
        simulate_net_diffusion(threshold=params[0], profile=params[1], p_removal=params[2], num_iter=time_steps)[
            'Infected']
    y_forecasted.index = y_actual.index

    mse = ((y_forecasted - y_actual) ** 2).mean()
    return np.float(mse)


def optimize_net_diffusion_model(y_actual, time_steps, maxiter=1, params=(0.18, 0.00001, 0.017)):
    # Parameters to optimize; passing in initial parameter values as a starting "guess": threshold, profile, p_removal
    x0 = np.array(params)

    # Find parameters that minimize Mean Squared Error
    result = minimize(mse, x0, args=(y_actual, time_steps), method='nelder-mead',
                      options={'xtol': 1e-8, 'maxiter': maxiter, 'disp': True})

    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('hierarchies', nargs='+', metavar='H',
                        help='Enter any number of hierarchies that you want to process.')
    inputs = parser.parse_args()
    process_newsgroups(*inputs.hierarchies)
