failures = []
class Post():
    def __init__(self, data):
        global failures
        raw = str(data.encode('latin1').decode('unicode_escape'))

        try:
            try:
                s = re.findall('(?<=[fF]rom: )\S+@[\w.]+', raw)[0]
            except IndexError:
                try:
                    s = re.findall('(?<=[fF]rom: )[\w \'<>,".\-@!+\\\\]+', raw )[0]
                    s = re.findall('(?<=<)[\S]+@[\S]+(?=>)', s)[0]
                except IndexError:
                    s = ''
            self.source = s

            d = re.findall('(?<=[Dd]ate: )[\w ,.:]+', raw)[0]
            try:
                self.date = dateparse(d)
            except ParserError:
                self.date = d

            ngroups = re.findall('(?<=[Nn]ewsgroups: )[\w ,.]+', raw )[0].split(',')

            self.newsgroups = ngroups

            s = re.findall('(?<=[Ss]ubject: )[[\]\S .,:-]+', raw)[0]
            self.subject = s

            try:
                mid = re.findall('(?<=[mM]essage-[iI][dD]: )[\S]+(?=\\n)', raw)[0]
                self.message_id = mid
            except IndexError as e:
                failures.append(e.__traceback__)
                self.message_id = f'no_mid_{len(failures)}'

            lines = [(len(x) > 0 and ':' not in x) for x in raw.split('\n')[1:]]
            self.body = '\n'.join(raw.split('\n')[np.argmax(lines)+1:])
        except IndexError as e:
            self.message_id = f'no_mid_{len(failures)}'
            failures.append(e.__traceback__)
    
    def __repr__(self):
        return f'Post ID: {self.message_id}'
    
    def __str__(self):
        return f'Post from: {self.source} with subject: {self.subject}'

    def __eq__(self, other):
        return self.message_id == other.message_id
    
    def __hash__(self):
        return hash(self.message_id)

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
        self.load()
        for post in posts:
            self.add(post)
    
    def save(self):
        with zpf.ZipFile(self.file_name, 'w') as f:
            with f.open(f'{self.name}.pkl', 'w') as jar:
                pickle.dump(self, jar)

    def load(self):
        try:
            with zpf.ZipFile(self.file_name, 'r') as f:
                with f.open(f'{self.name}.pkl', 'r') as jar:
                    oldset = pickle.load(jar)
                    for post in oldset:
                        self.add(post)
        except FileNotFoundError:
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