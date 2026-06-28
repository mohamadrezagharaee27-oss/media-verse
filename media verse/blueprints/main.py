from flask import Blueprint, render_template, request, abort
from flask_login import current_user
from sqlalchemy import or_
from app.models.upload import Upload
from app.models.user import User

main_bp = Blueprint('main', __name__)

CATEGORIES = [
    'gaming', 'music', 'education', 'sports', 'technology',
    'entertainment', 'news', 'travel', 'food', 'art', 'science', 'other'
]


@main_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    sort = request.args.get('sort', 'new')

    query = Upload.query

    if category and category in CATEGORIES:
        query = query.filter_by(category=category)

    if sort == 'popular':
        query = query.order_by(Upload.view_count.desc())
    elif sort == 'liked':
        # Sort by like count via subquery
        from sqlalchemy import func
        from app.models.upload import Like
        like_counts = db.session.query(
            Like.upload_id,
            func.count(Like.id).label('cnt')
        ).group_by(Like.upload_id).subquery()
        query = query.outerjoin(like_counts, Upload.id == like_counts.c.upload_id)\
                     .order_by(like_counts.c.cnt.desc().nullslast())
    else:
        query = query.order_by(Upload.created_at.desc())

    uploads = query.paginate(page=page, per_page=20, error_out=False)
    return render_template('main/index.html', uploads=uploads,
                           categories=CATEGORIES, current_category=category, sort=sort)


@main_bp.route('/search')
def search():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)

    upload_results = []
    user_results = []

    if q:
        upload_results = Upload.query.join(User).filter(
            or_(
                Upload.title.ilike(f'%{q}%'),
                Upload.description.ilike(f'%{q}%'),
                Upload.category.ilike(f'%{q}%'),
                User.username.ilike(f'%{q}%'),
                User.bio.ilike(f'%{q}%'),
            )
        ).order_by(Upload.view_count.desc()).limit(40).all()

        user_results = User.query.filter(
            or_(
                User.username.ilike(f'%{q}%'),
                User.display_name.ilike(f'%{q}%'),
                User.bio.ilike(f'%{q}%'),
            )
        ).limit(10).all()

    return render_template('main/search.html', q=q,
                           upload_results=upload_results,
                           user_results=user_results)


from app import db
