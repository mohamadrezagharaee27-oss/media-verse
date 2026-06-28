import cloudinary.uploader
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.upload import Upload, Notification

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/<username>')
def view(username):
    user = User.query.filter_by(username=username).first_or_404()
    uploads = Upload.query.filter_by(user_id=user.id)\
                          .order_by(Upload.created_at.desc()).all()

    is_following = False
    if current_user.is_authenticated and current_user.id != user.id:
        is_following = current_user.is_following(user)

    return render_template('profile/view.html', user=user, uploads=uploads,
                           is_following=is_following)


@profile_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'profile':
            current_user.display_name = request.form.get('display_name', '').strip() or current_user.display_name
            current_user.bio = request.form.get('bio', '').strip()

            avatar = request.files.get('avatar')
            if avatar and avatar.filename:
                try:
                    result = cloudinary.uploader.upload(
                        avatar, folder='mediaverse/avatars', resource_type='image',
                        transformation=[{'width': 256, 'height': 256, 'crop': 'fill'}]
                    )
                    current_user.avatar_url = result.get('secure_url', '')
                except Exception:
                    flash('Avatar upload failed.', 'error')

            db.session.commit()
            flash('Profile updated.', 'success')

        elif action == 'password':
            old_pw = request.form.get('old_password', '')
            new_pw = request.form.get('new_password', '')
            confirm = request.form.get('confirm_password', '')

            if not current_user.check_password(old_pw):
                flash('Current password is incorrect.', 'error')
            elif len(new_pw) < 6:
                flash('New password must be at least 6 characters.', 'error')
            elif new_pw != confirm:
                flash('Passwords do not match.', 'error')
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                flash('Password updated.', 'success')

        elif action == 'theme':
            theme = request.form.get('theme', 'dark')
            if theme in ('dark', 'light'):
                current_user.theme = theme
                db.session.commit()
                flash('Theme updated.', 'success')

        return redirect(url_for('profile.settings'))

    notifications = Notification.query.filter_by(
        recipient_id=current_user.id, is_read=False
    ).order_by(Notification.created_at.desc()).all()

    following = current_user.followed.all()
    followers = current_user.followers_list.all()

    return render_template('profile/settings.html',
                           notifications=notifications,
                           following=following,
                           followers=followers)


@profile_bp.route('/<int:user_id>/follow', methods=['POST'])
@login_required
def follow(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        abort(400)

    if not current_user.is_following(user):
        current_user.follow(user)
        # Create notification
        notif = Notification(
            recipient_id=user.id,
            sender_id=current_user.id,
            notification_type='follow',
            message=f'{current_user.display_name} started following you.'
        )
        db.session.add(notif)
        db.session.commit()

    return redirect(request.referrer or url_for('profile.view', username=user.username))


@profile_bp.route('/<int:user_id>/unfollow', methods=['POST'])
@login_required
def unfollow(user_id):
    user = User.query.get_or_404(user_id)
    if current_user.is_following(user):
        current_user.unfollow(user)
        db.session.commit()
    return redirect(request.referrer or url_for('profile.view', username=user.username))
