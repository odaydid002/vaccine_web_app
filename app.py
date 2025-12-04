from flask import Flask, render_template, request, redirect, session, jsonify
from datetime import datetime, timedelta
import bcrypt
import psycopg2
from datetime import date
from functools import wraps
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# اتصال PostgreSQL
conn = psycopg2.connect(
    dbname="vaccweb",
    user="postgres",
    password="20020429",
    host="localhost",
    port="5432"
)

# مفتاح الجلسة
app.secret_key = "development_key"

# مكان حفظ شهادات الميلاد المرفوعة
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXT = {'pdf', 'png', 'jpg', 'jpeg'}


# Ensure required DB columns exist (safe to run on startup)
def ensure_db_columns():
    with conn.cursor() as cur:
        # patients table additions
        cur.execute("""
            ALTER TABLE patients
            ADD COLUMN IF NOT EXISTS birthplace VARCHAR(255),
            ADD COLUMN IF NOT EXISTS weight_kg NUMERIC,
            ADD COLUMN IF NOT EXISTS maternal_health VARCHAR(255),
            ADD COLUMN IF NOT EXISTS emergency_flag BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS emergency_note TEXT,
            ADD COLUMN IF NOT EXISTS birth_certificate VARCHAR(255)
        """)

        # parent table: family booklet flag
        cur.execute("""
            ALTER TABLE parent
            ADD COLUMN IF NOT EXISTS family_booklet_declared BOOLEAN DEFAULT FALSE
        """)

        conn.commit()


# call on startup
try:
    ensure_db_columns()
except Exception:
    # don't crash the app if DB unreachable at import time
    pass


# ----------------------------
# دالة حماية المسارات حسب الدور
# ----------------------------
def require_role(role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):

            # تحقق من تسجيل الدخول
            if 'username' not in session:
                return redirect('/')

            # تحقق من الدور
            if session.get('role') != role:
                return redirect('/')

            return func(*args, **kwargs)
        return wrapper
    return decorator


# ----------------------------
# صفحة تسجيل الدخول
# ----------------------------
@app.route('/')
def home():

    # مستخدم مسجل دخول مسبقاً
    if 'role' in session:

        if session['role'] == "admin":
            return redirect('/admin')

        if session['role'] == "employee":
            return redirect('/main')

        if session['role'] == "client":
            return redirect('/client')

    # إذا لم يكن داخل الجلسة → أظهر صفحة تسجيل الدخول
    return render_template("login.html")


# ----------------------------
# تسجيل الدخول
# ----------------------------
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        return "❌ يرجى إدخال اسم المستخدم وكلمة المرور"

    with conn.cursor() as cur:
        cur.execute("SELECT id, username, password, role FROM users WHERE username=%s", (username,))
        user = cur.fetchone()

    if not user:
        return "❌ المستخدم غير موجود"

    user_id = user[0]
    db_pass = user[2]
    role = user[3]

    # مقارنة كلمة المرور
    if not bcrypt.checkpw(password.encode('utf-8'), db_pass.encode('utf-8')):
        return "❌ كلمة المرور غير صحيحة"

    # حفظ الجلسة
    session['user_id'] = user_id
    session['username'] = username
    session['role'] = role

    # التحويل بحسب الدور
    if role == "admin":
        return redirect("/admin")
    elif role == "employee":
        return redirect("/main")
    else:
        return redirect("/client")


# ----------------------------
# لوحة الإدارة (محمي)
# ----------------------------
@app.route('/admin')
@require_role("admin")
def admin_panel():
    with conn.cursor() as cur:
        cur.execute("SELECT id, username, role FROM users WHERE role='employee' OR role='client'")
        users = cur.fetchall()

        cur.execute("SELECT id FROM users WHERE role='employee'")
        employee_count = cur.fetchall()

        cur.execute("SELECT id FROM users WHERE role='client'")
        normal_users = cur.fetchall()

    return render_template(
        "admin.html",
        users=users,
        employee_count=employee_count,
        normal_users=normal_users
    )


# ----------------------------
# صفحة الموظف (محمي)
# ----------------------------
@app.route('/main')
@require_role("employee")
def main_page():
    with conn.cursor() as cur:
        # Fetch all patients with their vaccine info
        cur.execute("""
            SELECT
                p.id,
                p.fullname,
                p.birth_date,
                pa.phone,
                pa.id AS parent_id
            FROM patients p
            LEFT JOIN parent pa ON pa.child_id = p.id
            ORDER BY p.id DESC
        """)
        patients_rows = cur.fetchall()

        # Fetch vaccines for each patient
        cur.execute("""
            SELECT 
                pv.id,
                pv.patient_id,
                v.id,
                v.name,
                pv.scheduled_date,
                pv.status,
                pv.done_date
            FROM patient_vaccines pv
            JOIN vaccines v ON v.id = pv.vaccine_id
            ORDER BY pv.patient_id, pv.scheduled_date ASC, pv.id ASC
        """)
        vaccines_rows = cur.fetchall()

        # also fetch available vaccines to use in add-patient modal
        cur.execute("SELECT id, name FROM vaccines ORDER BY id")
        vaccines = cur.fetchall()

    from datetime import date
    today = date.today()

    # Organize vaccines by patient
    patient_vaccines_map = {}
    for vr in vaccines_rows:
        pv_id, patient_id, vaccine_id, vaccine_name, scheduled_date, status, done_date = vr
        if patient_id not in patient_vaccines_map:
            patient_vaccines_map[patient_id] = []
        patient_vaccines_map[patient_id].append({
            'id': pv_id,
            'vaccine_id': vaccine_id,
            'name': vaccine_name,
            'scheduled_date': scheduled_date,
            'status': status,
            'done_date': done_date
        })

    patients = []
    late_count = 0
    upcoming_count = 0

    for row in patients_rows:
        patient_id, fullname, birth_date, phone, parent_id = row
        
        # Get vaccines for this patient
        patient_vacs = patient_vaccines_map.get(patient_id, [])
        
        # Find next pending vaccine
        next_vaccine = None
        next_date = None
        for v in patient_vacs:
            if v['status'] == 'pending':
                next_date = v['scheduled_date']
                next_vaccine = v['name']
                break
        
        # Count late/upcoming
        if next_date and isinstance(next_date, date):
            if next_date < today:
                late_count += 1
            else:
                upcoming_count += 1

        patients.append({
            'id': patient_id,
            'fullname': fullname,
            'birth_date': birth_date,
            'phone': phone,
            'parent_id': parent_id,
            'next_date': next_date,
            'next_vaccine': next_vaccine,
            'vaccines': patient_vacs,
            'is_late': next_date and next_date < today if next_date else False
        })

    return render_template(
        "main.html",
        patients=patients,
        late_count=late_count,
        upcoming_count=upcoming_count,
        vaccines=vaccines
    )


@app.route('/parent/<int:parent_id>')
@require_role('employee')
def parent_detail(parent_id):
    with conn.cursor() as cur:
        # fetch parent row
        cur.execute("SELECT id, national_id, address, phone, parent_id, child_id FROM parent WHERE id=%s", (parent_id,))
        row = cur.fetchone()
        if not row:
            return "الولي غير موجود", 404

        parent = {
            'id': row[0],
            'national_id': row[1],
            'address': row[2],
            'phone': row[3],
            'user_id': row[4],
            'child_id': row[5]
        }

        # fetch all children for this user (there may be multiple parent rows linked to same user)
        cur.execute("SELECT p.id, p.fullname, p.birth_date, p.gender, p.birth_certificate, p.weight_kg FROM patients p JOIN parent pr ON pr.child_id = p.id WHERE pr.parent_id = %s", (parent['user_id'],))
        children_rows = cur.fetchall()

        children = []
        for c in children_rows:
            children.append({
                'id': c[0],
                'fullname': c[1],
                'birth_date': c[2],
                'gender': c[3],
                'birth_certificate': c[4],
                'weight_kg': c[5]
            })

        # fetch vaccines for these children
        # group vaccines per patient by scheduled_date (so vaccines on same date appear as one row)
        vaccines_map = {}
        ids = [c['id'] for c in children]
        if ids:
            sql = "SELECT pv.id, pv.patient_id, pv.vaccine_id, v.name, pv.scheduled_date, pv.status, pv.done_date FROM patient_vaccines pv JOIN vaccines v ON v.id = pv.vaccine_id WHERE pv.patient_id = ANY(%s) ORDER BY pv.scheduled_date, pv.id"
            cur.execute(sql, (ids,))
            pv_rows = cur.fetchall()
            # organize by patient -> scheduled_date -> list
            tmp = {}
            for pv in pv_rows:
                pid = pv[1]
                sched = pv[4] if pv[4] is not None else 'now'
                key = (pid, sched)
                tmp.setdefault(key, []).append(pv)

            # convert to grouped structure per patient
            for (pid, sched), pv_list in tmp.items():
                names = ' + '.join([p[3] for p in pv_list])
                statuses = [p[5] for p in pv_list]
                if all(s == 'done' for s in statuses):
                    grp_status = 'مؤكد'
                elif all(s != 'done' for s in statuses):
                    grp_status = 'قادم'
                else:
                    grp_status = 'مختلط'
                pv_ids = [p[0] for p in pv_list]
                group = {
                    'scheduled_date': (None if sched == 'now' else sched),
                    'names': names,
                    'status': grp_status,
                    'pv_ids': pv_ids
                }
                vaccines_map.setdefault(pid, []).append(group)

    return render_template('parent_detail.html', parent=parent, children=children, vaccines=vaccines_map)


@app.route('/parent_fragment/<int:parent_id>')
@require_role('employee')
def parent_fragment(parent_id):
    with conn.cursor() as cur:
        # fetch parent row
        cur.execute("SELECT id, national_id, address, phone, parent_id, child_id FROM parent WHERE id=%s", (parent_id,))
        row = cur.fetchone()
        if not row:
            return "الولي غير موجود", 404

        parent = {
            'id': row[0],
            'national_id': row[1],
            'address': row[2],
            'phone': row[3],
            'user_id': row[4],
            'child_id': row[5]
        }

        cur.execute("SELECT p.id, p.fullname, p.birth_date, p.gender, p.birth_certificate, p.weight_kg FROM patients p JOIN parent pr ON pr.child_id = p.id WHERE pr.parent_id = %s", (parent['user_id'],))
        children_rows = cur.fetchall()

        children = []
        for c in children_rows:
            children.append({
                'id': c[0],
                'fullname': c[1],
                'birth_date': c[2],
                'gender': c[3],
                'birth_certificate': c[4],
                'weight_kg': c[5]
            })

        # group vaccines per patient by scheduled_date
        vaccines_map = {}
        ids = [c['id'] for c in children]
        if ids:
            sql = "SELECT pv.id, pv.patient_id, pv.vaccine_id, v.name, pv.scheduled_date, pv.status, pv.done_date FROM patient_vaccines pv JOIN vaccines v ON v.id = pv.vaccine_id WHERE pv.patient_id = ANY(%s) ORDER BY pv.scheduled_date, pv.id"
            cur.execute(sql, (ids,))
            pv_rows = cur.fetchall()
            tmp = {}
            for pv in pv_rows:
                pid = pv[1]
                sched = pv[4] if pv[4] is not None else 'now'
                key = (pid, sched)
                tmp.setdefault(key, []).append(pv)

            for (pid, sched), pv_list in tmp.items():
                names = ' + '.join([p[3] for p in pv_list])
                statuses = [p[5] for p in pv_list]
                if all(s == 'done' for s in statuses):
                    grp_status = 'مؤكد'
                elif all(s != 'done' for s in statuses):
                    grp_status = 'قادم'
                else:
                    grp_status = 'مختلط'
                pv_ids = [p[0] for p in pv_list]
                group = {
                    'scheduled_date': (None if sched == 'now' else sched),
                    'names': names,
                    'status': grp_status,
                    'pv_ids': pv_ids
                }
                vaccines_map.setdefault(pid, []).append(group)

    return render_template('parent_fragment.html', parent=parent, children=children, vaccines=vaccines_map)


@app.route('/confirm_vaccine/<int:pv_id>', methods=['POST'])
@require_role('employee')
def confirm_vaccine(pv_id):
    with conn.cursor() as cur:
        cur.execute("UPDATE patient_vaccines SET status='done', done_date=%s WHERE id=%s", (datetime.now().date(), pv_id))
        # insert notification
        cur.execute("SELECT patient_id FROM patient_vaccines WHERE id=%s", (pv_id,))
        pid = cur.fetchone()
        if pid:
            cur.execute("INSERT INTO notifications (patient_id, message) VALUES (%s,%s)", (pid[0], 'تم تأكيد تلقي اللقاح'))
        conn.commit()
    # If AJAX request, return JSON so frontend can update without navigation
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    return redirect(request.referrer or '/main')


@app.route('/confirm_vaccines_group', methods=['POST'])
@require_role('employee')
def confirm_vaccines_group():
    data = None
    try:
        data = request.get_json(force=False, silent=True)
    except Exception:
        data = None

    pv_ids = []
    if data and isinstance(data, dict) and 'pv_ids' in data:
        pv_ids = data.get('pv_ids', [])
    else:
        # fallback to form data (comma separated)
        pv_ids_str = request.form.get('pv_ids')
        if pv_ids_str:
            pv_ids = [int(x) for x in pv_ids_str.split(',') if x.strip().isdigit()]

    if not pv_ids:
        return jsonify({'success': False, 'error': 'no_ids'})

    with conn.cursor() as cur:
        cur.execute("UPDATE patient_vaccines SET status='done', done_date=%s WHERE id = ANY(%s)", (datetime.now().date(), pv_ids))
        # add notifications per affected patient
        cur.execute("SELECT DISTINCT patient_id FROM patient_vaccines WHERE id = ANY(%s)", (pv_ids,))
        patients = cur.fetchall()
        for p in patients:
            cur.execute("INSERT INTO notifications (patient_id, message) VALUES (%s,%s)", (p[0], 'تم تأكيد تلقي مجموعة من اللقاحات'))
        conn.commit()

    return jsonify({'success': True})


@app.route('/unconfirm_vaccine/<int:pv_id>', methods=['POST'])
@require_role('employee')
def unconfirm_vaccine(pv_id):
    with conn.cursor() as cur:
        # set back to pending and clear done_date
        cur.execute("UPDATE patient_vaccines SET status='pending', done_date=NULL WHERE id=%s", (pv_id,))
        # insert notification
        cur.execute("SELECT patient_id FROM patient_vaccines WHERE id=%s", (pv_id,))
        pid = cur.fetchone()
        if pid:
            try:
                cur.execute("INSERT INTO notifications (patient_id, message) VALUES (%s,%s)", (pid[0], 'تم إلغاء تأكيد التطعيم'))
            except Exception:
                pass
        conn.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    return redirect(request.referrer or '/main')


@app.route('/unconfirm_vaccines_group', methods=['POST'])
@require_role('employee')
def unconfirm_vaccines_group():
    data = None
    try:
        data = request.get_json(force=False, silent=True)
    except Exception:
        data = None

    pv_ids = []
    if data and isinstance(data, dict) and 'pv_ids' in data:
        pv_ids = data.get('pv_ids', [])
    else:
        pv_ids_str = request.form.get('pv_ids')
        if pv_ids_str:
            pv_ids = [int(x) for x in pv_ids_str.split(',') if x.strip().isdigit()]

    if not pv_ids:
        return jsonify({'success': False, 'error': 'no_ids'})

    with conn.cursor() as cur:
        cur.execute("UPDATE patient_vaccines SET status='pending', done_date=NULL WHERE id = ANY(%s)", (pv_ids,))
        cur.execute("SELECT DISTINCT patient_id FROM patient_vaccines WHERE id = ANY(%s)", (pv_ids,))
        patients = cur.fetchall()
        for p in patients:
            try:
                cur.execute("INSERT INTO notifications (patient_id, message) VALUES (%s,%s)", (p[0], 'تم إلغاء تأكيد دفعة من التطعيمات'))
            except Exception:
                pass
        conn.commit()

    return jsonify({'success': True})


# ----------------------------
# تسجيل ولي — خطوة 1
# ----------------------------
@app.route('/register_parent', methods=['GET', 'POST'])
@require_role('employee')
def register_parent():
    if request.method == 'GET':
        return render_template('parent_register.html')

    # POST: validate and save parent
    first = request.form.get('first_name')
    last = request.form.get('last_name')
    birthplace = request.form.get('birthplace')
    address = request.form.get('address')
    phone = request.form.get('phone')
    national_id = request.form.get('national_id')
    family_booklet = True if request.form.get('family_booklet') else False

    if not first or not last or not national_id or len(national_id) != 18 or not national_id.isdigit():
        return "خطأ: الرجاء ملء الاسم واللقب ورقم التعريف الوطني من 18 رقماً."

    username = f"{first}.{last}"
    password = bcrypt.hashpw(national_id.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    with conn.cursor() as cur:
        # create user
        cur.execute("INSERT INTO users (username, password, role) VALUES (%s,%s,%s) RETURNING id",
                    (username, password, 'client'))
        user_id = cur.fetchone()[0]

        # insert parent (child_id will be set when newborn saved)
        cur.execute("INSERT INTO parent (national_id, address, phone, parent_id, child_id, family_booklet_declared) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                    (national_id, address, phone, user_id, None, family_booklet))
        parent_id = cur.fetchone()[0]

        conn.commit()

    # redirect to newborn registration with parent id
    return redirect(f"/register_newborn/{parent_id}")


# ----------------------------
# تسجيل المولود — خطوة 2
# ----------------------------
@app.route('/register_newborn/<int:parent_id>', methods=['GET', 'POST'])
@require_role('employee')
def register_newborn(parent_id):
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM vaccines ORDER BY id")
        vaccines = cur.fetchall()

    if request.method == 'GET':
        return render_template('newborn_register.html', parent_id=parent_id, vaccines=vaccines)

    # POST: save newborn, link to parent, handle vaccine selections and file
    first = request.form.get('first_name')
    last = request.form.get('last_name')
    full_name = (first or '') + (' ' + last if last else '')
    weight = None
    try:
        weight = float(request.form.get('weight')) if request.form.get('weight') else None
    except Exception:
        weight = None
    gender = request.form.get('gender')
    maternal_health = request.form.get('maternal_health')
    emergency = True if request.form.get('emergency') else False
    emergency_note = request.form.get('emergency_note')
    birth_cert = request.files.get('birth_certificate')
    selected = request.form.getlist('vaccines')

    if not first or not gender:
        return "خطأ: يرجى إدخال اسم المولود والجنس."

    with conn.cursor() as cur:
        # insert patient
        cur.execute("INSERT INTO patients (fullname, birth_date, gender, birthplace, weight_kg, maternal_health, emergency_flag, emergency_note, birth_certificate) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                    (full_name, None, gender, None, weight, maternal_health, emergency, emergency_note, None))
        patient_id = cur.fetchone()[0]

        # link parent to child: update parent.child_id
        cur.execute("UPDATE parent SET child_id=%s WHERE id=%s", (patient_id, parent_id))

        # save birth certificate
        if birth_cert and birth_cert.filename:
            filename = secure_filename(birth_cert.filename)
            ext = filename.rsplit('.',1)[-1].lower() if '.' in filename else ''
            if ext in ALLOWED_EXT:
                uniq = f"{patient_id}_{int(datetime.now().timestamp())}_{filename}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], uniq)
                birth_cert.save(save_path)
                birth_cert_path = os.path.join('static','uploads',uniq)
                cur.execute("UPDATE patients SET birth_certificate=%s WHERE id=%s", (birth_cert_path, patient_id))

        # handle vaccines
        for vid in selected:
            try:
                v_id = int(vid)
            except Exception:
                continue
            given = True if request.form.get(f'given_{v_id}') else False
            if given:
                cur.execute("INSERT INTO patient_vaccines (patient_id, vaccine_id, dose_number, scheduled_date, status, done_date) VALUES (%s,%s,%s,%s,%s,%s)",
                            (patient_id, v_id, 1, None, 'done', None))
            else:
                cur.execute("INSERT INTO patient_vaccines (patient_id, vaccine_id, dose_number, scheduled_date, status) VALUES (%s,%s,%s,%s,%s)",
                            (patient_id, v_id, 1, None, 'pending'))

        # notify
        cur.execute("INSERT INTO notifications (patient_id, message) VALUES (%s,%s)", (patient_id, f"تم تسجيل المولود {full_name}"))

        conn.commit()

    return redirect('/main')

# ----------------------------
# صفحة العميل (محمي)
# ----------------------------
@app.route('/client')
@require_role("client")
def client_page():
    user_id = session.get('user_id')
    username = session.get('username')
    
    with conn.cursor() as cur:
        # جلب بيانات الأب/الولي
        cur.execute("""
            SELECT id, national_id, address, phone, family_booklet_declared
            FROM parent
            WHERE parent_id = %s
        """, (user_id,))
        parent_data = cur.fetchone()
        
        # جلب الأطفال والتطعيمات
        children = []
        vaccines_data = {}
        
        if parent_data:
            parent_id = parent_data[0]
            cur.execute("""
                SELECT id, fullname, birth_date, gender, weight_kg, birth_certificate
                FROM patients
                WHERE id IN (SELECT child_id FROM parent WHERE parent_id = %s)
            """, (parent_id,))
            
            children_rows = cur.fetchall()
            
            for child in children_rows:
                child_id = child[0]
                children.append({
                    'id': child_id,
                    'fullname': child[1],
                    'birth_date': child[2],
                    'gender': child[3],
                    'weight_kg': child[4],
                    'birth_certificate': child[5]
                })
                
                # جلب التطعيمات لكل طفل
                cur.execute("""
                    SELECT pv.id, v.name, pv.scheduled_date, pv.status, pv.done_date, pv.dose_number
                    FROM patient_vaccines pv
                    JOIN vaccines v ON v.id = pv.vaccine_id
                    WHERE pv.patient_id = %s
                    ORDER BY pv.scheduled_date ASC, pv.id ASC
                """, (child_id,))
                
                vaccines_rows = cur.fetchall()
                vaccines_data[child_id] = []
                
                for vac in vaccines_rows:
                    vaccines_data[child_id].append({
                        'id': vac[0],
                        'name': vac[1],
                        'scheduled_date': vac[2],
                        'status': vac[3],
                        'done_date': vac[4],
                        'dose_number': vac[5]
                    })
    
    parent = None
    if parent_data:
        parent = {
            'id': parent_data[0],
            'national_id': parent_data[1],
            'address': parent_data[2],
            'phone': parent_data[3],
            'family_booklet_declared': parent_data[4]
        }
    
    from datetime import date
    today = date.today()
    
    # حساب الإحصائيات
    total_vaccines = sum(len(vaccines_data.get(child['id'], [])) for child in children)
    completed_vaccines = 0
    pending_vaccines = 0
    late_vaccines = 0
    
    for child_id in vaccines_data:
        for vac in vaccines_data[child_id]:
            if vac['status'] == 'done':
                completed_vaccines += 1
            elif vac['status'] == 'pending':
                if vac['scheduled_date'] and vac['scheduled_date'] < today:
                    late_vaccines += 1
                else:
                    pending_vaccines += 1
    
    stats = {
        'total_vaccines': total_vaccines,
        'completed_vaccines': completed_vaccines,
        'pending_vaccines': pending_vaccines,
        'late_vaccines': late_vaccines
    }
    
    return render_template(
        "client.html",
        username=username,
        parent=parent,
        children=children,
        vaccines=vaccines_data,
        stats=stats,
        now=today
    )


@app.route('/download_certificate/<int:child_id>')
@require_role('client')
def download_certificate(child_id):
    user_id = session.get('user_id')
    # verify child belongs to this client
    with conn.cursor() as cur:
        # Allow employees to download any certificate; otherwise ensure the child belongs to this client
        allowed = False
        if session.get('role') == 'client':
            allowed = True
        else:
            # get parent rows linked to the child; check both parent record id and parent.parent_id (user id)
            cur.execute("SELECT id, parent_id FROM parent WHERE child_id=%s", (child_id,))
            parent_links = cur.fetchall()
            for pl in parent_links:
                # pl = (id, parent_id)
                try:
                    if not pl:
                        continue
                    parent_row_id = pl[0]
                    parent_user_id = pl[1]
                    if parent_user_id == user_id or parent_row_id == user_id:
                        allowed = True
                        break
                except Exception:
                    continue

        if not allowed:
            return "غير مصرح", 403

        # fetch child info
        cur.execute("SELECT id, fullname, birth_date FROM patients WHERE id=%s", (child_id,))
        row = cur.fetchone()
        if not row:
            return "الطفل غير موجود", 404
        child = {'id': row[0], 'fullname': row[1], 'birth_date': row[2]}

        # fetch all vaccines for this child
        cur.execute("SELECT v.name, pv.dose_number, pv.status, pv.done_date FROM patient_vaccines pv JOIN vaccines v ON v.id=pv.vaccine_id WHERE pv.patient_id=%s ORDER BY pv.dose_number", (child_id,))
        pv_rows = cur.fetchall()

    vaccines = []
    all_done = True
    for p in pv_rows:
        name, dose, status, done_date = p
        vaccines.append({'name': name, 'dose': dose, 'status': status, 'done_date': done_date})
        if status != 'done':
            all_done = False

    if not all_done:
        return "لا يمكن تنزيل الشهادة: ليست كل التطعيمات مكتملة.", 400

    # render certificate HTML
    html = render_template('certificate.html', child=child, vaccines=vaccines, issued_date=datetime.now().date())

    # try to convert to PDF using pdfkit (wkhtmltopdf) if available
    try:
        import pdfkit
        # basic options for decent rendering
        options = {
            'encoding': 'UTF-8',
            'enable-local-file-access': None
        }
        pdf = pdfkit.from_string(html, False, options=options)
        from flask import make_response
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        filename = f"certificate_{child['id']}.pdf"
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception:
        # fallback: return HTML for printing or saving as PDF client-side
        return html


# ----------------------------
# صفحة الإحصائيات للموظف
# ----------------------------
@app.route('/stats')
@require_role('employee')
def stats_page():
    # period: daily, weekly, yearly
    period = request.args.get('period', 'weekly')
    from datetime import date, timedelta
    today = date.today()
    if period == 'daily':
        start = today
    elif period == 'yearly':
        start = today - timedelta(days=365)
    else:
        # weekly default (last 7 days)
        start = today - timedelta(days=6)

    end = today

    with conn.cursor() as cur:
        # basic totals
        cur.execute("SELECT COUNT(*) FROM patients")
        total_patients = cur.fetchone()[0] or 0

        cur.execute("SELECT COUNT(*) FROM parent")
        total_parents = cur.fetchone()[0] or 0

        # vaccines given (done) in period grouped by vaccine name
        cur.execute(
            "SELECT v.name, COUNT(*) FROM patient_vaccines pv JOIN vaccines v ON v.id=pv.vaccine_id WHERE pv.status='done' AND pv.done_date BETWEEN %s AND %s GROUP BY v.name ORDER BY COUNT(*) DESC",
            (start, end)
        )
        vaccines_done = cur.fetchall()

        # distinct patients who received at least one vaccine in this period
        cur.execute(
            "SELECT COUNT(DISTINCT patient_id) FROM patient_vaccines WHERE status='done' AND done_date BETWEEN %s AND %s",
            (start, end)
        )
        patients_vaccinated = cur.fetchone()[0] or 0

        # pending scheduled in period
        cur.execute(
            "SELECT COUNT(*) FROM patient_vaccines WHERE status='pending' AND scheduled_date BETWEEN %s AND %s",
            (start, end)
        )
        pending_in_period = cur.fetchone()[0] or 0

        # late pending overall
        cur.execute(
            "SELECT COUNT(*) FROM patient_vaccines WHERE status='pending' AND scheduled_date < %s",
            (today,)
        )
        late_total = cur.fetchone()[0] or 0

        # vaccines by status overall
        cur.execute("SELECT status, COUNT(*) FROM patient_vaccines GROUP BY status")
        by_status = cur.fetchall()

    # convert rows to friendly structures
    vaccines_done_list = [{'name': r[0], 'count': r[1]} for r in vaccines_done]
    by_status_dict = {r[0]: r[1] for r in by_status}

    return render_template('stats.html',
                           period=period,
                           start=start,
                           end=end,
                           total_patients=total_patients,
                           total_parents=total_parents,
                           vaccines_done=vaccines_done_list,
                           patients_vaccinated=patients_vaccinated,
                           pending_in_period=pending_in_period,
                           late_total=late_total,
                           by_status=by_status_dict)

# ----------------------------
# إضافة موظف جديد
# ----------------------------
@app.route('/add_employee', methods=['POST'])
@require_role("admin")
def add_user():
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        return "❌ يرجى تعبئة جميع الحقول"

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            (username, hashed_password, "employee")
        )
        conn.commit()

    return redirect("/admin")


# ----------------------------
# إضافة مريض 
# ----------------------------
@app.route('/add_patient', methods=['POST'])
@require_role("employee")
def add_patient():
    nationalId = request.form.get("p-national-id")
    # parent (guardian)
    fname = request.form.get("pt-fname")
    lname = request.form.get("pt-lname")
    phone = request.form.get("p-phone")
    address = request.form.get("p-address")
    family_booklet = True if request.form.get("p-family-booklet") == 'on' else False

    # newborn
    p_first = request.form.get("p-first")
    p_last = request.form.get("p-last")
    name = (p_first or "") + (" " + p_last if p_last else "")
    birth = request.form.get("p-birth")
    birthplace = request.form.get("p-birthplace")
    gender = request.form.get('p-gender')
    weight = None
    try:
        weight = float(request.form.get('p-weight')) if request.form.get('p-weight') else None
    except Exception:
        weight = None

    maternal_health = request.form.get('maternal-health')
    emergency_flag = True if request.form.get('p-emergency') == 'on' else False
    emergency_note = request.form.get('p-emergency-note')

    # vaccines selected and given markers
    selected_vaccines = request.form.getlist('vaccines')

    # birth certificate file
    birth_cert = request.files.get('birth_certificate')

    is_foreign = True if request.form.get('p-is-foreign') == 'on' or request.form.get('p-is-foreign') else False

    # normalize nationalId
    if nationalId:
        nationalId = nationalId.strip()
        if nationalId == '':
            nationalId = None

    with conn.cursor() as cur:

        #  1. التحقق إذا كان الوالد موجود مسبقًا
        # If nationalId provided, check by it; otherwise check by phone to avoid duplicates for foreign parents
        if nationalId:
            cur.execute("SELECT id FROM parent WHERE national_id = %s", (nationalId,))
        else:
            cur.execute("SELECT id FROM parent WHERE phone = %s", (phone,))
        parent_record = cur.fetchone()

        #  2. إدخال بيانات الطفل (المريض) وجلب رقم المعرّف بعد الإدخال
        cur.execute(
            """
            INSERT INTO patients (fullname, birth_date, gender, birthplace, weight_kg, maternal_health, emergency_flag, emergency_note, birth_certificate)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (name, birth, gender, birthplace, weight, maternal_health, emergency_flag, emergency_note, None)
        )
        patient_id = cur.fetchone()[0]

        # handle birth certificate file saving
        birth_cert_path = None
        if birth_cert and birth_cert.filename:
            filename = secure_filename(birth_cert.filename)
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            if ext in ALLOWED_EXT:
                # make filename unique
                uniq = f"{patient_id}_{int(datetime.now().timestamp())}_{filename}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], uniq)
                birth_cert.save(save_path)
                birth_cert_path = os.path.join('static', 'uploads', uniq)
                # update patient record with file path
                cur.execute("UPDATE patients SET birth_certificate=%s WHERE id=%s", (birth_cert_path, patient_id))

        #  3. إذا لم يكن الوالد موجود → نقوم بإنشاء حساب مستخدم جديد + سجل الوالد
        if parent_record is None:

            # create password: use nationalId when present, otherwise generate a random password
            import uuid
            raw_pw = nationalId if nationalId else uuid.uuid4().hex
            password = bcrypt.hashpw(raw_pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # insert user
            cur.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s) RETURNING id",
                ( (fname + "." + lname)[:60], password, "client")
            )
            user_id = cur.fetchone()[0]

            # insert parent record; nationalId may be None for foreign parents
            cur.execute(
                """INSERT INTO parent (national_id, address, phone, parent_id, child_id, family_booklet_declared)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (nationalId, address, phone, user_id, patient_id, family_booklet)
            )
            parent_record_id = cur.fetchone()[0]
        else:
            # parent exists: update child link (in case adding another child)
            try:
                existing_parent_id = parent_record[0]
                cur.execute("UPDATE parent SET child_id=%s, address=%s, phone=%s WHERE id=%s", (patient_id, address, phone, existing_parent_id))
            except Exception:
                pass

        # ----------------------------
        # توليد جدول التطعيمات للطفل (حذف/تخطي اللقاحات التي أدخلت مباشرة عبر الفورم)
        # ----------------------------
        # حساب عمر الطفل بالشهور
        cur.execute("SELECT birth_date FROM patients WHERE id=%s", (patient_id,))
        birth_date = cur.fetchone()[0]

        # handle vaccines explicitly selected in form
        for vid in selected_vaccines:
            try:
                v_id = int(vid)
            except Exception:
                continue
            given = True if request.form.get(f'given_{v_id}') == 'on' else False
            if given:
                cur.execute(
                    """
                    INSERT INTO patient_vaccines (patient_id, vaccine_id, dose_number, scheduled_date, status, done_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (patient_id, v_id, 1, birth_date, 'done', birth_date)
                )
            else:
                cur.execute(
                    """
                    INSERT INTO patient_vaccines (patient_id, vaccine_id, dose_number, scheduled_date, status)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (patient_id, v_id, 1, birth_date, 'pending')
                )

        # now insert scheduled vaccines from vaccine_schedule (skip those already selected)
        cur.execute("SELECT vaccine_id, dose_number, age_months FROM vaccine_schedule")
        schedule_rows = cur.fetchall()

        for sched in schedule_rows:
            vaccine_id = sched[0]
            dose_number = sched[1]
            age_m = sched[2]

            if str(vaccine_id) in selected_vaccines:
                continue

            cur.execute("""
                INSERT INTO patient_vaccines (patient_id, vaccine_id, dose_number, scheduled_date)
                VALUES (%s, %s, %s, %s)
            """, (
                patient_id,
                vaccine_id,
                dose_number,
                birth_date + timedelta(days=age_m * 30)
            ))

        cur.execute("""
            INSERT INTO notifications (patient_id, message)
            VALUES (%s, %s)
        """, (
            patient_id,
            f"تم إنشاء جدول التطعيمات تلقائياً للطفل {name}"
        ))


        #  حفظ كل العمليات في قاعدة البيانات
        conn.commit()

    #  إعادة التوجيه إلى الصفحة الرئيسية
    return redirect("/main")


# ----------------------------
# حذف المستخدم
# ----------------------------
@app.route('/delete_user/<int:user_id>')
@require_role("admin")
def delete_user(user_id):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
        conn.commit()
    return redirect("/admin")


# ----------------------------
# تعديل المستخدم
# ----------------------------
@app.route('/edit_user', methods=['POST'])
@require_role("admin")
def edit_user():
    user_id = request.form['user_id']
    username = request.form['username']
    password = request.form['password']

    with conn.cursor() as cur:

        if password.strip() == "":
            cur.execute("UPDATE users SET username=%s WHERE id=%s", (username, user_id))
        else:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cur.execute("UPDATE users SET username=%s, password=%s WHERE id=%s",
                        (username, hashed_password, user_id))

        conn.commit()

    return redirect("/admin")


# ----------------------------
# تسجيل الخروج
# ----------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ----------------------------
# تشغيل التطبيق
# ----------------------------
if __name__ == '__main__':
    app.run(debug=True)
