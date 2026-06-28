from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.upload import Upload, Like, Comment, Notification

api_bp = Blueprint('api', __name__)


@api_bp.route('/like/<int:upload_id>', methods=['POST'])
@login_required
def toggle_like(upload_id):
    upload = Upload.query.get_or_404(upload_id)
    existing = Like.query.filter_by(upload_id=upload_id, user_id=current_user.id).first()

    if existing:
        db.session.delete(existing)
        liked = False
    else:
        like = Like(upload_id=upload_id, user_id=current_user.id)
        db.session.add(like)
        liked = True
        # Notify uploader
        if upload.user_id != current_user.id:
            notif = Notification(
                recipient_id=upload.user_id,
                sender_id=current_user.id,
                notification_type='like',
                upload_id=upload_id,
                message=f'{current_user.display_name} liked your upload "{upload.title}".'
            )
            db.session.add(notif)

    db.session.commit()
    return jsonify({'liked': liked, 'count': upload.like_count})


@api_bp.route('/comment/<int:upload_id>', methods=['POST'])
@login_required
def add_comment(upload_id):
    upload = Upload.query.get_or_404(upload_id)
    content = request.json.get('content', '').strip() if request.is_json else \
              request.form.get('content', '').strip()

    if not content or len(content) > 2000:
        return jsonify({'error': 'Invalid comment'}), 400

    comment = Comment(
        content=content,
        upload_id=upload_id,
        user_id=current_user.id
    )
    db.session.add(comment)

    # Notify uploader
    if upload.user_id != current_user.id:
        notif = Notification(
            recipient_id=upload.user_id,
            sender_id=current_user.id,
            notification_type='comment',
            upload_id=upload_id,
            message=f'{current_user.display_name} commented on "{upload.title}".'
        )
        db.session.add(notif)

    db.session.commit()

    return jsonify({
        'id': comment.id,
        'content': comment.content,
        'author_name': current_user.display_name,
        'author_username': current_user.username,
        'author_avatar': current_user.avatar,
        'created_at': comment.created_at.isoformat(),
        'count': upload.comment_count
    })


@api_bp.route('/comment/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    upload_id = comment.upload_id
    db.session.delete(comment)
    db.session.commit()
    upload = Upload.query.get(upload_id)
    return jsonify({'success': True, 'count': upload.comment_count if upload else 0})


@api_bp.route('/comment/<int:comment_id>', methods=['PUT'])
@login_required
def edit_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    content = data.get('content', '').strip()
    if not content or len(content) > 2000:
        return jsonify({'error': 'Invalid content'}), 400

    comment.content = content
    db.session.commit()
    return jsonify({'success': True, 'content': comment.content})


@api_bp.route('/notifications/read', methods=['POST'])
@login_required
def mark_notifications_read():
    from app.models.upload import Notification
    Notification.query.filter_by(
        recipient_id=current_user.id, is_read=False
    ).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/notifications/count')
@login_required
def notification_count():
    from app.models.upload import Notification
    count = Notification.query.filter_by(
        recipient_id=current_user.id, is_read=False
    ).count()
    return jsonify({'count': count})
