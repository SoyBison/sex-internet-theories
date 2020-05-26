import numpy as np
import glob
import zipfile as zpf
import os
import dataset
import re
from dateutil.parser import parse as dateparse
from dateutil.parser import ParserError
from io import FileIO
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
        raw = data.replace('\\t', '').split('\\n')

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
        d = d.strip('\\t')
        try:
            return dateparse(d, ignoretz=True)
        except ParserError:
            try:
                return dateparse(re.findall('.+ [\\d:]+', d)[0])
            except IndexError:
                return None

    @staticmethod
    def ngroups_finder(raw):
        ng = Post.firstmatch(re.compile(r'[Nn]ewsgroups: '), raw)[12:].split(',')
        ng = [n for n in ng if n != '']
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

    def save(self, loc='../Data/usenet.db'):

        # TODO: I have a suspicion this doesn't work right, check up on that.
        db = dataset.connect(f'sqlite:///{loc}')
        post_table = db['posts']
        newsgroup_table = db['newsgroups']
        data_dump = {'source': self.source,
                     'date': self.date,
                     'subject': self.subject,
                     'message_id': self.message_id,
                     'body': self.body}
        post_table.upsert(data_dump, ['message_id'])
        news_data = {group.replace('.', '_').replace('-', '$'): 1 for group in self.newsgroups}
        news_data['message_id'] = self.message_id
        newsgroup_table.upsert(news_data, ['message_id'])

    @classmethod
    def load(cls, message_id, loc='../Data/usenet.db'):
        db = dataset.connect(f'sqlite:///{loc}')
        post_table = db['posts']
        data_dump = post_table.find_one(message_id=message_id)
        newsgroup_table = db['newsgroups']
        newsgroup_dump = newsgroup_table.find_one(message_id=message_id)
        post = cls.__new__(cls)
        data_dump.pop('id')
        newsgroup_dump.pop('id')
        post.__dict__.update(data_dump)
        post.newsgroups = [k.replace('_', '.').replace('$', '-') for k in newsgroup_dump if newsgroup_dump[k]]
        return post


class Newsgroup(dict):
    def __init__(self, name, posts=(), loc='auto'):
        super().__init__(self)
        hierarchy = name.split('.')[0]
        if loc == 'auto':
            if not os.path.exists(f'../Data/{hierarchy}'):
                loc = '.'
            else:
                loc = f'../Data/{hierarchy}'

        self.file_name = loc + '/' + name + '.zip'
        self.name = name
        self.load()
        for post in posts:
            self[post.message_id] = post

    def save(self, loc="../Data/usenet.db"):
        db = dataset.connect(f'sqlite:///{loc}')
        if not os.path.exists(loc):
            seed = self.pop(list(self.keys())[0])
            seed.save()
        disk_mids = {d['message_id'] for d in db.query('SELECT message_id FROM posts')}
        mem_mids = {post.message_id for post in self.values()}
        new_mids = mem_mids - disk_mids
        tar_posts = []
        tar_newsgroups = []
        pbar = tqdm(new_mids)
        pbar.set_description(f'Processing save data for {self.name}')
        for mid in pbar:
            post = self[mid]
            data_dump = {'source': post.source,
                         'date': post.date,
                         'subject': post.subject,
                         'message_id': post.message_id,
                         'body': post.body}
            news_data = {group.replace('.', '_').replace('-', '$'): 1 for group in post.newsgroups if group != ''}
            tar_posts.append(data_dump)
            tar_newsgroups.append(news_data)
        print(f'Saving {self.name}...')
        db['posts'].insert_many(tar_posts, chunk_size=100000)
        db['newsgroups'].insert_many(tar_newsgroups, chunk_size=100000)

    def load(self, loc="../Data/usenet.db"):
        print(f'Loading {self.name}...')
        db = dataset.connect(f'sqlite:///{loc}')
        raise NotImplementedError

        disk_mids = {d['message_id'] for d in db.query('SELECT message_id FROM posts')}
        mem_mids = {post.message_id for post in self.values()}
        new_mids = disk_mids - mem_mids
        all_ngs = db['newsgroups'].columns
        name_list = self.name.split('.')
        name_depth = len(name_list)
        all_ngs = [x.split('_') for x in all_ngs]
        relevants = ['_'.join(ng) for ng in all_ngs if ng[:name_depth] == name_list]

        tar_mids = relevants
        for mid in tqdm(new_mids):
            self[mid] = Post.load(mid)

    @classmethod
    def from_mbox(cls, file_name, rm=False, save=True):
        name = file_name.split('/')[-1][:-9]
        hierarchy = name.split('.')[0]
        if not os.path.exists(f'../Data/{hierarchy}'):
            os.mkdir(f'../Data/{hierarchy}')
        self = cls(name, loc=f'../Data/{hierarchy}')
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
    def from_hierarchy(cls, hierarchy):
        toplevel = hierarchy.split('.')[0]
        big_group = cls(hierarchy)
        all_boards = glob.glob(f'../Data/usenet-{toplevel}/{hierarchy}*')
        for group in all_boards:
            big_group.update(**Newsgroup.from_mbox(group, save=False))
        return big_group
