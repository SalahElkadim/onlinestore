
import cloudinary.uploader
# احنا واقفين على اننا نعدل ملفات الموديلز والسيراليزرز بما يناسب كلاودينري والفيوز كمان

def upload_image(file, folder='general', public_id=None):
    """
    Upload أي صورة لـ Cloudinary مع transformations.
    Returns: dict فيه url و public_id
    """
    options = {
        'folder':          folder,
        'use_filename':    True,
        'unique_filename': True,
        'overwrite':       False,
        'resource_type':   'image',
        'transformation': [
            {'quality': 'auto:good'},   # ضغط تلقائي ذكي
            {'fetch_format': 'auto'},   # WebP للمتصفحات اللي تدعمه
        ],
    }
    if public_id:
        options['public_id'] = public_id
        options['overwrite'] = True

    result = cloudinary.uploader.upload(file, **options)
    return {
        'url':       result['secure_url'],
        'public_id': result['public_id'],
    }


def upload_product_image(file, product_id):
    return upload_image(
        file,
        folder=f'products/{product_id}',
        transformation_extra={'width': 800, 'height': 800, 'crop': 'limit'},
    )


def upload_avatar(file, user_id):
    return upload_image(
        file,
        folder='avatars',
        public_id=f'avatar_{user_id}',
        # دايماً يـ overwrite نفس الـ public_id
    )


def upload_category_image(file, category_id):
    return upload_image(
        file,
        folder=f'categories',
        public_id=f'category_{category_id}',
    )


def delete_image(public_id):
    """حذف صورة من Cloudinary بالـ public_id."""
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get('result') == 'ok'
    except Exception:
        return False


def get_optimized_url(public_id, width=None, height=None, quality='auto'):
    """
    إنشاء Transformation URL ديناميكي.
    مثال: get_optimized_url('products/1/img', width=400)
    """
    transformation = [
        {'quality': quality},
        {'fetch_format': 'auto'},
    ]
    if width or height:
        transform = {'crop': 'fill'}
        if width:
            transform['width'] = width
        if height:
            transform['height'] = height
        transformation.append(transform)

    return cloudinary.CloudinaryImage(public_id).build_url(
        transformation=transformation,
        secure=True,
    )