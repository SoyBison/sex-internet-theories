failures = []
class Post():
    def __init__(self, data):
        global failures
        raw = str(data.encode('latin1').decode('unicode_escape'))

        try:
            s = re.findall('(?<=[fF]rom: )\S+@[\w.]+', raw)[0]
        except IndexError:
            try:
                s = re.findall('(?<=[fF]rom: )[\w \'~`<>%,)(".&\-@!+\\\\]+', raw )[0]
                s = re.findall('(?<=<)[\S ]+@[\S ]+(?=>)', s)[0]
            except IndexError:
                s = ''
        self.source = s

        d = re.findall('(?<=[Dd]ate: )[\w ,.:]+', raw)[0]
        try:
            self.date = dateparse(d, ignoretz=True)
        except ParserError:
            self.date = None
        try:
            ngroups = re.findall('(?<=[Nn]ewsgroups: )[\w ,.]+', raw )[0].split(',')

            self.newsgroups = ngroups
        except:
            self.newsgroups = []
        try:
            s = re.findall('(?<=[Ss]ubject: )[[\S .,:-]]+', raw)[0]
            self.subject = s
        except IndexError:
            self.subject = ''

        try:
            mid = re.findall('(?<=[mM]essage-[iI][dD]: )[\S]+(?=\\n)', raw)[0]
            self.message_id = mid
        except IndexError as e:
            failures.append(e.__traceback__)
            self.message_id = f'no_mid_{len(failures)}'

        lines = [(len(x) > 0 and ':' not in x) for x in raw.split('\n')[1:]]
        self.body = '\n'.join(raw.split('\n')[np.argmax(lines)+1:])

    
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
        db = dataset.connect(f'sqlite:///{loc}')
        post_table = db['posts']
        newsgroup_table = db['newsgroups']
        data_dump = {'source': self.source,
                     'date': self.date,
                     'subject': self.subject,
                     'message_id': self.message_id,
                     'body': self.body}
        post_table.upsert(data_dump, ['message_id'])
        news_data = {group.replace('.', '_'): 1 for group in self.newsgroups}
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
        post.newsgroups = [k.replace('_', '.') for k in newsgroup_dump if newsgroup_dump[k]]
        return post
        


class Newsgroup(set):
    def __init__(self, name, posts=[], loc='auto'):
        super().__init__(self)
        hierarchy = name.split('.')[0]
        if loc == 'auto':
            if not os.path.exists(f'../Data/{hierarchy}'):
                loc = '.'
            else:
                loc = f'../Data/{hierarchy}'

        self.file_name = loc + '/' + name + '.zip'
        self.name = name
        # self.load()
        for post in posts:
            self.add(post)
    

    
    def retrieve_post(self, mid):
        post = [post for post in self if post.message_id == mid][0]
        return post
    
    def save(self, loc="../Data/usenet.db"):
        print(f'Saving {self.name}...')
        db = dataset.connect(f'sqlite:///{loc}')
        disk_mids = {d['message_id'] for d in db.query('SELECT message_id FROM posts')}
        mem_mids = {post.message_id for post in self}
        new_mids = mem_mids - disk_mids
        tar_posts = []
        tar_newsgroups = []
        for mid in new_mids:
            post = self.retrieve_post(mid)
            data_dump = {'source': post.source,
                     'date': post.date,
                     'subject': post.subject,
                     'message_id': post.message_id,
                     'body': post.body}
            news_data = {group.replace('.', '_'): 1 for group in post.newsgroups if group != ''}
            tar_posts.append(data_dump)
            tar_newsgroups.append(news_data)
        db['posts'].insert_many(tar_posts)
        db['newsgroups'].insert_many(tar_newsgroups)
        

    def load(self, loc="../Data/usenet.db"):
        pass
        
    
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
            raw.seek(0,0)

        post_iterator = usenet_reader(raw)
        with tqdm(usenet_reader(raw), total=size) as pbar:
            pbar.set_description(f'Loading {name}... ')
            for post, line in usenet_reader(raw):
                self.add(Post(post))
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
            big_group |= Newsgroup.from_mbox(group, save=False)
        return big_group