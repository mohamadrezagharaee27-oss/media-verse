from datetime import datetime, timezone
from app import db


class Upload(db.Model):
    __tablename__ = 'uploads'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    category = db.Column(db.String(50), nullable=False, default='other')
    file_url = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)  # video, image, audio, pdf, document, archive, other
    thumbnail_url = db.Column(db.String(500), default='')
    public_id = db.Column(db.String(255), default='')  # Cloudinary public_id
    file_size = db.Column(db.BigInteger, default=0)
    duration = db.Column(db.Float, default=0)  # for video/audio in seconds
    view_count = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    comments = db.relationship('Comment', backref='upload', lazy='dynamic', cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='upload', lazy='dynamic', cascade='all, delete-orphan')
    views = db.relationship('View', backref='upload', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.count()

    @property
    def thumbnail(self):
        if self.thumbnail_url:
            return self.thumbnail_url
        # Default thumbnails per type
        defaults = {
            'video': 'https://placehold.co/640x360/1a1a2e/6366f1?text=VIDEO',
            'image': self.file_url if self.file_url else 'https://placehold.co/640x360/1a1a2e/6366f1?text=IMAGE',
            'audio': 'https://placehold.co/640x360/1a1a2e/6366f1?text=AUDIO',
            'pdf': 'https://placehold.co/640x360/1a1a2e/6366f1?text=PDF',
            'document': 'https://placehold.co/640x360/1a1a2e/6366f1?text=DOC',
            'archive': 'https://placehold.co/640x360/1a1a2e/6366f1?text=ZIP',
        }
        if self.file_type == 'image':
            return self.file_url
        return defaults.get(self.file_type, 'https://placehold.co/640x360/1a1a2e/6366f1?text=FILE')

    def __repr__(self):
        return f'<Upload {self.title}>'


class View(db.Model):
    __tablename__ = 'views'

    id = db.Column(db.Integer, primary_key=True)
    upload_id = db.Column(db.Integer, db.ForeignKey('uploads.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    viewed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('upload_id', 'user_id', name='unique_user_view'),
    )


class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    upload_id = db.Column(db.Integer, db.ForeignKey('uploads.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Comment {self.id}>'


class Like(db.Model):
    __tablename__ = 'likes'

    id = db.Column(db.Integer, primary_key=True)
    upload_id = db.Column(db.Integer, db.ForeignKey('uploads.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('upload_id', 'user_id', name='unique_like'),
    )

    def __repr__(self):
        return f'<Like upload={self.upload_id} user={self.user_id}>'


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notification_type = db.Column(db.String(30), nullable=False)  # follow, comment, like
    upload_id = db.Column(db.Integer, db.ForeignKey('uploads.id'), nullable=True)
    message = db.Column(db.String(300), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    sender = db.relationship('User', foreign_keys=[sender_id])
    upload = db.relationship('Upload', foreign_keys=[upload_id])

    def __repr__(self):
        return f'<Notification {self.notification_type} for user {self.recipient_id}>'
