import os
import cloudinary
import cloudinary.uploader
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from app import db
from app.models.upload import Upload, View, Like, Comment
from app.models.user import User

upload_bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {
    'video': {'mp4', 'webm', 'avi', 'mov', 'mkv', 'flv', 'm4v'},
    'audio': {'mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a'},
    'image': {'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp'},
    'pdf': {'pdf'},
    'document': {'doc', 'docx', 'txt', 'rtf', 'odt', 'xlsx', 'xls', 'pptx', 'ppt', 'csv'},
    'archive': {'zip', 'rar', '7z', 'tar', 'gz'}
}

CATEGORIES = [
    'gaming', 'music', 'education', 'sports', 'technology',
    'entertainment', 'news', 'travel', 'food', 'art', 'science', 'other'
]


def get_file_type(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    for ftype, exts in ALLOWED_EXTENSIONS.items():
        if ext in exts:
            return ftype
    return 'other'


def allowed_file(filename):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[-1].lower()
    all_exts = set()
    for s in ALLOWED_EXTENSIONS.values():
        all_exts.update(s)
    return ext in all_exts


def upload_to_cloudinary(file, resource_type='auto', folder='mediaverse'):
    """Upload file to Cloudinary and return result."""
    try:
        result = cloudinary.uploader.upload(
            file,
            resource_type=resource_type,
            folder=folder,
            chunk_size=6 * 1024 * 1024  # 6MB chunks for large files
        )
        return result
    except Exception as e:
        current_app.logger.error(f'Cloudinary upload error: {e}')
        raise


@upload_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():

    current_app.logger.info("========== NEW REQUEST ==========")
    current_app.logger.info(f"Method: {request.method}")

    if request.method == 'POST':

        current_app.logger.info("POST STARTED")
        current_app.logger.info(request.form)
        current_app.logger.info(request.files)
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'other')
        file = request.files.get('file')
        thumbnail_file = request.files.get('thumbnail')

        errors = []
        if not title:
            errors.append('Title is required.')
        if not file or file.filename == '':
            errors.append('Please select a file to upload.')
        elif not allowed_file(file.filename):
            errors.append('File type not supported.')
        if category not in CATEGORIES:
            category = 'other'

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('upload/new.html', categories=CATEGORIES, form_data=request.form)

        try:
            file_type = get_file_type(file.filename)
            # Determine cloudinary resource_type
            if file_type == 'video':
                res_type = 'video'
            elif file_type in ('image',):
                res_type = 'image'
            elif file_type == 'audio':
                res_type = 'video'  # Cloudinary uses 'video' for audio too
            else:
                res_type = 'raw'

            # Upload main file
            current_app.logger.info("Uploading to Cloudinary...")
            result = upload_to_cloudinary(file, resource_type=res_type)
            current_app.logger.info("Cloudinary upload finished")
            file_url = result.get('secure_url', '')
            public_id = result.get('public_id', '')
            file_size = result.get('bytes', 0)
            duration = result.get('duration', 0) or 0

            # Thumbnail
            thumbnail_url = ''
            if thumbnail_file and thumbnail_file.filename:
                thumb_result = upload_to_cloudinary(thumbnail_file, resource_type='image', folder='mediaverse/thumbs')
                thumbnail_url = thumb_result.get('secure_url', '')
            elif file_type == 'video':
                # Auto-generate thumbnail from video
                thumbnail_url = cloudinary.utils.cloudinary_url(
                    public_id, resource_type='video', format='jpg',
                    transformation=[{'width': 640, 'height': 360, 'crop': 'fill'}]
                )[0]
            elif file_type == 'image':
                thumbnail_url = file_url

            upload = Upload(
                title=title,
                description=description,
                category=category,
                file_url=file_url,
                file_type=file_type,
                thumbnail_url=thumbnail_url,
                public_id=public_id,
                file_size=file_size,
                duration=duration,
                user_id=current_user.id
            )
            db.session.add(upload)
            db.session.commit()
            flash('Upload successful!', 'success')
            return redirect(url_for('upload.view', upload_id=upload.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Upload failed: {e}')
            flash('Upload failed. Please try again.', 'error')
            return render_template('upload/new.html', categories=CATEGORIES, form_data=request.form)

    return render_template('upload/new.html', categories=CATEGORIES)


@upload_bp.route('/<int:upload_id>')
def view(upload_id):
    upload = Upload.query.get_or_404(upload_id)

    # View counting logic
    viewed_key = f'viewed_{upload_id}'
    if viewed_key not in request.cookies:
        # Check if user already viewed (logged in)
        already_viewed = False
        if current_user.is_authenticated:
            from app.models.upload import View as ViewModel
            already_viewed = ViewModel.query.filter_by(
                upload_id=upload_id, user_id=current_user.id
            ).first() is not None

        if not already_viewed:
            try:
                ip = request.remote_addr
                if current_user.is_authenticated:
                    view_record = View(upload_id=upload_id, user_id=current_user.id, ip_address=ip)
                else:
                    # For anonymous, check by IP (simple approach)
                    from app.models.upload import View as ViewM
                    exists = ViewM.query.filter_by(upload_id=upload_id, ip_address=ip, user_id=None).first()
                    if exists:
                        already_viewed = True
                    else:
                        view_record = View(upload_id=upload_id, ip_address=ip)

                if not already_viewed:
                    db.session.add(view_record)
                    upload.view_count = (upload.view_count or 0) + 1
                    db.session.commit()
            except Exception:
                db.session.rollback()

    # Related uploads
    related = Upload.query.filter(
        Upload.category == upload.category,
        Upload.id != upload_id
    ).order_by(Upload.view_count.desc()).limit(10).all()

    # Check if current user liked
    user_liked = False
    if current_user.is_authenticated:
        user_liked = Like.query.filter_by(
            upload_id=upload_id, user_id=current_user.id
        ).first() is not None

    comments = Comment.query.filter_by(upload_id=upload_id)\
                            .join(User, Comment.user_id == User.id)\
                            .order_by(Comment.created_at.desc()).all()

    response = render_template('upload/view.html', upload=upload, related=related,
                               user_liked=user_liked, comments=comments)
    # Set cookie to prevent duplicate views
    from flask import make_response
    resp = make_response(response)
    resp.set_cookie(f'viewed_{upload_id}', '1', max_age=86400)  # 24h
    return resp


@upload_bp.route('/<int:upload_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(upload_id):
    upload = Upload.query.get_or_404(upload_id)
    if upload.user_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        upload.title = request.form.get('title', '').strip() or upload.title
        upload.description = request.form.get('description', '').strip()
        upload.category = request.form.get('category', upload.category)

        # Optional new thumbnail
        thumb = request.files.get('thumbnail')
        if thumb and thumb.filename:
            try:
                result = upload_to_cloudinary(thumb, resource_type='image', folder='mediaverse/thumbs')
                upload.thumbnail_url = result.get('secure_url', '')
            except Exception:
                flash('Thumbnail upload failed.', 'error')

        db.session.commit()
        flash('Upload updated.', 'success')
        return redirect(url_for('upload.view', upload_id=upload_id))

    return render_template('upload/edit.html', upload=upload, categories=CATEGORIES)


@upload_bp.route('/<int:upload_id>/delete', methods=['POST'])
@login_required
def delete(upload_id):
    upload = Upload.query.get_or_404(upload_id)
    if upload.user_id != current_user.id:
        abort(403)

    # Delete from Cloudinary
    if upload.public_id:
        try:
            res_type = 'video' if upload.file_type in ('video', 'audio') else \
                       'image' if upload.file_type == 'image' else 'raw'
            cloudinary.uploader.destroy(upload.public_id, resource_type=res_type)
        except Exception:
            pass

    db.session.delete(upload)
    db.session.commit()
    flash('Upload deleted.', 'success')
    return redirect(url_for('main.index'))
