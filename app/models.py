# coding: utf-8
from app import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from flask import current_app, request
from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
import bleach
import hashlib      #计算电子邮件的MD5散列值库

class Permission:
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_ARTICLES = 0x04
    MODERATE_COMMENTS = 0x08
    ADMINISTER = 0x80

class Follow(db.Model):
    __tablename__ = 'follows'
    # Follow被添加了follwoer和followed引用，
    # 使用z.follower  z.followed可以返回具体对象

    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)       #关注人ID
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)       #被关注者ID
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64),unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)

    def __repr__(self):
        return '<Role %r>' % self.name

    @staticmethod
    def insert_roles():     #静态方法加入角色
        roles = {
            'User': (Permission.FOLLOW |
                     Permission.COMMENT |
                     Permission.WRITE_ARTICLES, True),
            'Moderator': (Permission.FOLLOW |
                          Permission.COMMENT |
                          Permission.WRITE_ARTICLES |
                          Permission.MODERATE_COMMENTS, False),
            "Administrator": (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()



class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))   #不直接储存密码，而储存密码的哈希值
    email = db.Column(db.String(64), unique=True, index=True)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    confirmed = db.Column(db.Boolean, default=False)
    # 与Follow表中所有follower_id为自己的行关联
    # foreign_keys=[Follow.follower_id]：明确关联外键
    # db.backref('follower', lazy='joined')：创建一个为follower的反向引用
    # backref=db.backref('follower', lazy='joined')：把上边的添加为Follow表的反向引用。Follow.follower返回关注者对象
    who_i_followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    # 与上边的相同，为Follow表添加了follower和followed引用，
    # 所以Follow表可以直接用Follow(follower= 对象 ,followed= 对象)来创建新实例。
    who_followed_me = db.relationship('Follow',
                          foreign_keys=[Follow.followed_id],
                          backref=db.backref('followed', lazy='joined'),
                          lazy='dynamic',
                          cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()


    @property
    def password(self):     #调用密码不可见
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):   #设置密码，储存为密码的哈希值
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User %r>' % self.username

    def can(self, permissions):     #检查权限
        return self.role is not None and (self.role.permissions & permissions) == permissions

    def is_administrator(self):     #检查管理员权限
        return self.can(Permission.ADMINISTER)

    def ping(self):     #获取最后登陆时间
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def generate_confirmation_token(self, expiration=3600):     #设置认证密钥
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):       #认证检查密钥
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def reset_password(self, token):    #重置密码密钥检查
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        else:
            return True

    def changeemail(self, token):      #重置邮箱密钥检查
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        else:
            return True

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'https://www.gravatar.com/avatar'
        hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating
        )

    @staticmethod
    def generate_fake(count=100):       #用forgery_py自动生成大量用户
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u = User(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(True),
                     password=forgery_py.lorem_ipsum.word(),
                     confirmed=True,
                     name=forgery_py.name.full_name(),
                     location=forgery_py.address.city(),
                     about_me=forgery_py.lorem_ipsum.sentence(),
                     member_since=forgery_py.date.date(True))
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

    # 关注用户：先判断是否已关注，如果没关注，给Follow表创建新行

    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    # 取消关注：查询自己的who_i_followed中是否有目标用户，如果有，删除。
    def unfollow(self, user):
        f = self.who_i_followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    # 判断是否关注某个用户：用自己的who_i_followed关联到Follow表中关联的记录，记录中所有的follower_id都是
    # 自己，所以筛选followed_id是否有要查目标，有返回True，没有返回False。

    def is_following(self, user):
        return self.who_i_followed.filter_by(followed_id=user.id).first() is not None

    # 判断是否被某个用户关注

    def is_followed_by(self, user):
        return self.who_followed_me.filter_by(follower_id=user.id).first() is not None


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)       #存储原始数据
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    body_html = db.Column(db.Text)      #存储转换后的HTML数据

    @staticmethod
    def generate_fake(count=100):       #用forgery_py生成文章
        from random import seed, randint
        import forgery_py

        seed()
        user_count = User.query.count()
        for i in range(count):
            u = User.query.offset(randint(0, user_count - 1)).first()
            p = Post(body=forgery_py.lorem_ipsum.sentences(randint(1, 3)),
                     timestamp=forgery_py.date.date(True),
                     author=u)
            db.session.add(p)
            db.session.commit()

    @staticmethod           #用静态方法来把文章原始数据转换成HTML
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True
        ))

db.event.listen(Post.body, 'set', Post.on_changed_body)     #数据库环境监听，调用上边的静态方法

