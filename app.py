import streamlit as st
import sqlite3
import os
import pandas as pd
import datetime
import re

# إعداد صفحة الويب لتكون واسعة ومنسقة
st.set_page_config(
    page_title="منظومة HSS المتكاملة",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "erp_database.db")

st.markdown("""
    
""", unsafe_allow_html=True)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name_ar TEXT, name_en TEXT, client TEXT, site_name TEXT,
            job_title TEXT, governorate TEXT, district TEXT, hire_date TEXT,
            hire_type TEXT, social_status TEXT, qualification TEXT, address TEXT,
            site_salary REAL DEFAULT 0, insurance_status TEXT, insurance_no TEXT,
            bank_account TEXT, phone1 TEXT, phone2 TEXT, national_id TEXT,
            birth_date TEXT, age INTEGER, gender TEXT, doc_id_card TEXT,
            doc_birth_cert TEXT, doc_criminal_record TEXT, doc_military_cert TEXT,
            doc_qualification TEXT, doc_photos TEXT, doc_labor_office TEXT,
            doc_insurance_print TEXT, employment_status TEXT, source_sheet TEXT,
            is_deleted INTEGER DEFAULT 0, mother_name TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS custom_dropdowns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            item_value TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)
    c.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES ('company_name', '✦ منظومة HSS المتكاملة')")
    c.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES ('company_branch', 'نظام إدارة الموارد والتشغيل')")
    conn.commit()
    conn.close()

init_db()

def get_setting(key, default=""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key, value):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

NAME_DICTIONARY = {
    "محمد": "Mohamed", "محمود": "Mahmoud", "أحمد": "Ahmed", "هشام": "Hesham",
    "مصطفى": "Mostafa", "علي": "Ali", "حسن": "Hassan", "حسين": "Hussein",
    "إبراهيم": "Ibrahim", "سيد": "Sayed", "عمر": "Omar", "خالد": "Khaled"
}

def arabic_to_english(name):
    if not name: return ""
    words = name.strip().split()
    return " ".join([NAME_DICTIONARY.get(w, w.capitalize()) for w in words])

def parse_nid(nid):
    nid = str(nid).strip()
    if len(nid) != 14 or not nid.isdigit(): return None, None, None
    century = "19" if nid[0] == '2' else "20" if nid[0] == '3' else None
    if not century: return None, None, None
    try:
        y, m, d = int(century + nid[1:3]), int(nid[3:5]), int(nid[5:7])
        bdate = datetime.date(y, m, d)
        today = datetime.date.today()
        age = today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))
        gender = "ذكر" if int(nid[12]) % 2 != 0 else "أنثى"
        return bdate.strftime("%Y-%m-%d"), age, gender
    except:
        return None, None, None

def get_dropdown_items(cat_name, default_list=[]):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT DISTINCT item_value FROM custom_dropdowns WHERE category = ? ORDER BY item_value", (cat_name,))
    items = [r[0].strip() for r in c.fetchall() if r[0]]
    if not items and default_list:
        items = list(default_list)
        for it in items:
            c.execute("INSERT OR IGNORE INTO custom_dropdowns (category, item_value) VALUES (?, ?)", (cat_name, it))
        conn.commit()
    conn.close()
    return sorted(list(set(items)))

def remove_custom_dropdown_item(cat, item):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM custom_dropdowns WHERE category = ? AND item_value = ?", (cat, item))
    conn.commit()
    conn.close()

def add_custom_dropdown_item(cat, item):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO custom_dropdowns (category, item_value) VALUES (?, ?)", (cat, item))
    conn.commit()
    conn.close()

def check_users_exist():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    cnt = c.fetchone()[0]
    conn.close()
    return cnt > 0

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not check_users_exist():
    st.title("🛡️ إعداد المسؤول الأول (First Admin Setup)")
    with st.form("setup_form"):
        new_user = st.text_input("اسم المستخدم المسؤول:")
        new_pass = st.text_input("كلمة المرور:", type="password")
        submit_setup = st.form_submit_button("إنشاء الحساب والبدء")
        if submit_setup:
            if new_user and new_pass:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (new_user, new_pass, "Super Admin"))
                conn.commit()
                conn.close()
                st.success("تم إنشاء الحساب بنجاح! قم بتحديث الصفحة.")
                st.rerun()
            else:
                st.warning("يرجى إدخال اسم المستخدم وكلمة المرور.")
    st.stop()

if not st.session_state.logged_in:
    st.title("🔐 تسجيل الدخول | منظومة HSS")
    with st.form("login_form"):
        u = st.text_input("اسم المستخدم:")
        p = st.text_input("كلمة المرور:", type="password")
        btn_login = st.form_submit_button("تسجيل الدخول")
        if btn_login:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (u, p))
            user = c.fetchone()
            conn.close()
            if user:
                st.session_state.logged_in = True
                st.session_state.username = u
                st.rerun()
            else:
                st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")
    st.stop()

company_name = get_setting("company_name", "✦ منظومة HSS المتكاملة")
company_branch = get_setting("company_branch", "نظام إدارة الموارد والتشغيل")

st.sidebar.title(company_name)
st.sidebar.caption(company_branch)
st.sidebar.markdown("---")

nav = st.sidebar.radio("التنقل بين الأقسام:", ["👥 سجلات العاملين", "➕ إضافة موظف جديد", "📄 ملف موظف تفصيلي", "⚙️ إعدادات النظام"])

if nav == "👥 سجلات العاملين":
    st.title("📊 سجلات الموظفين والقوة")
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM employees WHERE is_deleted=0")
    total_emp = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM employees WHERE is_deleted=0 AND (source_sheet='القوة' OR employment_status LIKE '%يعمل%')")
    active_emp = c.fetchone()[0]
    conn.close()

    col1, col2 = st.columns(2)
    col1.metric("إجمالي السجلات النشطة", total_emp)
    col2.metric("القوة الحالية (على رأس العمل)", active_emp)
    st.markdown("---")

    search_query = st.text_input("🔍 بحث عام (بالكود، الرقم القومي، أو الاسم):")
    
    conn = sqlite3.connect(DB_FILE)
    if search_query:
        if search_query.isdigit():
            df = pd.read_sql_query("SELECT code, name_ar, client, site_name, job_title, phone1, employment_status FROM employees WHERE is_deleted=0 AND (code=? OR national_id=?)", conn, params=(search_query, search_query))
        else:
            df = pd.read_sql_query("SELECT code, name_ar, client, site_name, job_title, phone1, employment_status FROM employees WHERE is_deleted=0 AND name_ar LIKE ?", conn, params=(f"%{search_query}%",))
    else:
        df = pd.read_sql_query("SELECT code, name_ar, client, site_name, job_title, phone1, employment_status FROM employees WHERE is_deleted=0 ORDER BY CAST(code AS INTEGER) ASC", conn)
    conn.close()

    st.dataframe(df, use_container_width=True)

elif nav == "➕ إضافة موظف جديد":
    st.title("➕ تسجيل موظف جديد في النظام")
    
    clients = get_dropdown_items('client')
    jobs = get_dropdown_items('job_title')
    govs = get_dropdown_items('governorate', ["القاهرة", "الجيزة", "الإسكندرية", "الدقهلية", "الغربية", "القليوبية"])
    socials = get_dropdown_items('social_status', ["أعزب", "متزوج", "مطلق", "أرمل"])
    hires = get_dropdown_items('hire_type', ["المرة الأولى", "إعادة تعيين", "انتداب"])
    inss = get_dropdown_items('insurance_status', ["Yes", "NO", "قيد الإجراء"])

    with st.form("add_employee_form"):
        st.subheader("1. البيانات الوظيفية والتعاقدية")
        col1, col2 = st.columns(2)
        with col1:
            code = st.text_input("كود الموظف الفريد (*):")
            name_ar = st.text_input("الاسم الكامل بالعربية (*):")
            client = st.selectbox("العميل / البنك (*):", clients if clients else ["غير محدد"])
            job_title = st.selectbox("الوظيفة / الرتبة (*):", jobs if jobs else ["فرد أمن"])
            governorate = st.selectbox("المحافظة (*):", govs)
        with col2:
            name_en = st.text_input("الاسم بالإنجليزية (تلقائي):", value=arabic_to_english(st.session_state.get('name_ar', '')))
            site_name = st.text_input("الموقع / الفرع:")
            district = st.text_input("الحي / المركز:")
            phone1 = st.text_input("موبايل 1 الأساسي (*):")
            phone2 = st.text_input("موبايل 2 الإضافي:")

        st.subheader("2. البيانات الشخصية والمالية")
        col3, col4 = st.columns(2)
        with col3:
            qualification = st.text_input("المؤهل الدراسي:")
            mother_name = st.text_input("اسم الأم الثلاثي:")
            social_status = st.selectbox("الحالة الاجتماعية:", socials)
            hire_type = st.selectbox("نوع التعيين:", hires)
            hire_date = st.text_input("تاريخ التعيين (YYYY-MM-DD):", value=str(datetime.date.today()))
        with col4:
            address = st.text_input("العنوان بالتفصيل:")
            site_salary = st.number_input("راتب الموقع الأساسي:", min_value=0.0, value=0.0)
            insurance_status = st.selectbox("الحالة التأمينية:", inss)
            insurance_no = st.text_input("الرقم التأميني:")
            bank_account = st.text_input("رقم الحساب البنكي / المحفظة:")

        st.subheader("3. الرقم القومي والاستنتاج التلقائي")
        national_id = st.text_input("الرقم القومي (14 رقماً) (*):", max_chars=14)
        
        bdate, age, gender = parse_nid(national_id)
        if bdate:
            st.success(f"✓ تم التحقق من الرقم القومي | تاريخ الميلاد: {bdate} | السن: {age} سنة | النوع: {gender}")
        elif national_id:
            st.error("⚠️ الرقم القومي غير مكتمل أو غير صحيح (يجب أن يكون 14 رقماً يبدأ بـ 2 أو 3).")

        st.subheader("4. مسوغات التعيين والمستندات")
        doc_cols = st.columns(4)
        doc_choices = ["أصل", "صورة", "ناقص"]
        
        d_id = doc_cols[0].selectbox("بطاقة الرقم القومي", doc_choices, index=2)
        d_birth = doc_cols[1].selectbox("شهادة الميلاد", doc_choices, index=2)
        d_crim = doc_cols[2].selectbox("الفيش الجنائي", doc_choices, index=2)
        d_mil = doc_cols[3].selectbox("شهادة التجنيد", doc_choices, index=2)
        
        doc_cols2 = st.columns(4)
        d_qual = doc_cols2[0].selectbox("المؤهل الدراسي", doc_choices, index=2)
        d_pic = doc_cols2[1].selectbox("الصور الشخصية", doc_choices, index=2)
        d_labor = doc_cols2[2].selectbox("كعب العمل", doc_choices, index=2)
        d_ins = doc_cols2[3].selectbox("البرينت التأميني", doc_choices, index=2)

        def map_doc(val):
            return 'Y' if val == 'اصل' or val == 'أصل' else 'C' if val == 'صورة' else 'N'

        submit_btn = st.form_submit_button("💾 حفظ وتأكيد بيانات الموظف")
        if submit_btn:
            if not code or not name_ar or not phone1 or not national_id:
                st.warning("يرجى ملء الحقول الإلزامية (الكود، الاسم الكامل، الموبايل الأول، الرقم القومي).")
            elif not bdate:
                st.error("الرقم القومي غير صحيح ولا يمكن الحفظ.")
            else:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("SELECT code FROM employees WHERE code = ? OR national_id = ?", (code, national_id))
                exists = cursor.fetchone()
                if exists:
                    st.error("كود الموظف أو الرقم القومي مسجل مسبقاً في النظام!")
                    conn.close()
                else:
                    record = (
                        code, name_ar, arabic_to_english(name_ar), client, site_name, job_title,
                        governorate, district, hire_date, hire_type, social_status, qualification,
                        address, site_salary, insurance_status, insurance_no, bank_account,
                        phone1, phone2, national_id, bdate, age, gender,
                        map_doc(d_id), map_doc(d_birth), map_doc(d_crim), map_doc(d_mil),
                        map_doc(d_qual), map_doc(d_pic), map_doc(d_labor), map_doc(d_ins),
                        "يعمل", "القوة", 0, mother_name
                    )
                    cursor.execute("""
                        INSERT INTO employees (
                            code, name_ar, name_en, client, site_name, job_title, governorate, district,
                            hire_date, hire_type, social_status, qualification, address,
                            site_salary, insurance_status, insurance_no, bank_account,
                            phone1, phone2, national_id, birth_date, age, gender,
                            doc_id_card, doc_birth_cert, doc_criminal_record, doc_military_cert,
                            doc_qualification, doc_photos, doc_labor_office, doc_insurance_print,
                            employment_status, source_sheet, is_deleted, mother_name
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, record)
                    conn.commit()
                    conn.close()
                    st.success("تم تسجيل الموظف وحفظ بياناته بنجاح تام!")

elif nav == "📄 ملف موظف تفصيلي":
    st.title("📄 عرض الملف الكامل والمستندات للموظف")
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT code, name_ar FROM employees WHERE is_deleted=0 ORDER BY CAST(code AS INTEGER) ASC")
    emp_list = [f"{row[0]} - {row[1]}" for row in c.fetchall()]
    conn.close()

    if not emp_list:
        st.warning("لا توجد سجلات موظفين مسجلة حتى الآن.")
    else:
        selected_emp = st.selectbox("اختر الموظف:", emp_list)
        if selected_emp:
            code_val = selected_emp.split(" - ")[0]
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM employees WHERE code = ?", (code_val,))
            row = cursor.fetchone()
            columns = [col[0] for col in cursor.description]
            conn.close()
            
            if row:
                emp = dict(zip(columns, row))
                st.markdown(f"### 👤 {emp.get('name_ar')} (كود: {emp.get('code')})")
                
                b1, b2, b3, b4 = st.columns(4)
                b1.info(f"**العميل:** {emp.get('client') or 'غير محدد'}")
                b2.info(f"**الموقع:** {emp.get('site_name') or 'غير محدد'}")
                b3.info(f"**الوظيفة:** {emp.get('job_title') or 'غير محدد'}")
                b4.info(f"**الحالة:** {emp.get('employment_status') or 'يعمل'}")

                st.markdown("---")
                st.subheader("📋 البيانات الشخصية والتعاقدية والمالية")
                
                d1, d2, d3 = st.columns(3)
                d1.write(f"**الرقم القومي:** {emp.get('national_id') or '-'}")
                d1.write(f"**اسم الأم:** {emp.get('mother_name') or '-'}")
                d1.write(f"**تاريخ الميلاد:** {emp.get('birth_date') or '-'}")
                d1.write(f"**السن المحسوب:** {emp.get('age') or '-'} سنة")
                d1.write(f"**النوع:** {emp.get('gender') or '-'}")
                
                d2.write(f"**المحافظة:** {emp.get('governorate') or '-'}")
                d2.write(f"**الحي/المركز:** {emp.get('district') or '-'}")
                d2.write(f"**العنوان:** {emp.get('address') or '-'}")
                d2.write(f"**الموبايل الأساسي:** {emp.get('phone1') or '-'}")
                d2.write(f"**الموبايل الإضافي:** {emp.get('phone2') or '-'}")

                d3.write(f"**المؤهل الدراسي:** {emp.get('qualification') or '-'}")
                d3.write(f"**الحالة الاجتماعية:** {emp.get('social_status') or '-'}")
                d3.write(f"**نوع التعيين:** {emp.get('hire_type') or '-'}")
                d3.write(f"**تاريخ التعيين:** {emp.get('hire_date') or '-'}")
                d3.write(f"**الراتب الأساسي:** {emp.get('site_salary') or 0} ج.م")
                d3.write(f"**الحالة التأمينية:** {emp.get('insurance_status') or '-'}")
                d3.write(f"**الرقم التأميني:** {emp.get('insurance_no') or '-'}")
                d3.write(f"**الحساب البنكي:** {emp.get('bank_account') or '-'}")

                st.markdown("---")
                st.subheader("🗂️ حالة مسوغات التعيين والمستندات الرسمية")
                
                docs_map = [
                    ("بطاقة الرقم القومي", emp.get('doc_id_card')),
                    ("شهادة الميلاد", emp.get('doc_birth_cert')),
                    ("الفيش الجنائي", emp.get('doc_criminal_record')),
                    ("شهادة التجنيد", emp.get('doc_military_cert')),
                    ("المؤهل الدراسي", emp.get('doc_qualification')),
                    ("الصور الشخصية", emp.get('doc_photos')),
                    ("كعب العمل", emp.get('doc_labor_office')),
                    ("البرينت التأميني", emp.get('doc_insurance_print'))
                ]

                cols_doc = st.columns(4)
                for i, (doc_name, doc_val) in enumerate(docs_map):
                    col_target = cols_doc[i % 4]
                    if doc_val == 'Y':
                        col_target.success(f"**{doc_name}**\n\n🟢 أصل متوفر")
                    elif doc_val == 'C':
                        col_target.warning(f"**{doc_name}**\n\n🟡 صورة متوفرة")
                    else:
                        col_target.error(f"**{doc_name}**\n\n🔴 ناقص ✕")

elif nav == "⚙️ إعدادات النظام":
    st.title("⚙️ لوحة إعدادات النظام")
    
    tab1, tab2, tab3 = st.tabs(["🏢 بيانات الشركة", "📋 القوائم المنسدلة", "💾 تصدير وإكسيل"])
    
    with tab1:
        st.subheader("إعدادات الهوية والمؤسسة")
        cname_input = st.text_input("اسم الشركة:", value=company_name)
        cbranch_input = st.text_input("فرع الشركة:", value=company_branch)
        if st.button("حفظ بيانات الشركة"):
            set_setting("company_name", cname_input)
            set_setting("company_branch", cbranch_input)
            st.success("تم التحديث بنجاح! قم بتحديث الصفحة.")

    with tab2:
        st.subheader("إدارة القوائم المنسدلة")
        cat = st.selectbox("اختر القائمة:", ["client", "job_title", "governorate", "social_status", "hire_type", "insurance_status"])
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT DISTINCT item_value FROM custom_dropdowns WHERE category = ? ORDER BY item_value", (cat,))
        items = [r[0] for r in c.fetchall()]
        conn.close()

        st.write("العناصر الحالية:")
        for item in items:
            c1, c2 = st.columns([4, 1])
            c1.text(item)
            if c2.button("حذف", key=f"del_{cat}_{item}"):
                remove_custom_dropdown_item(cat, item)
                st.success(f"تم حذف {item}")
                st.rerun()

        new_val = st.text_input("إضافة عنصر جديد:")
        if st.button("إضافة للقائمة"):
            if new_val:
                add_custom_dropdown_item(cat, new_val)
                st.success("تمت الإضافة بنجاح!")
                st.rerun()

    with tab3:
        st.subheader("تصدير تقرير الإكسيل")
        if st.button("📊 تحميل شيت الإكسيل الكامل"):
            conn = sqlite3.connect(DB_FILE)
            df_all = pd.read_sql_query("SELECT * FROM employees", conn)
            conn.close()
            
            file_path = "HSS_Workforce_Export.xlsx"
            df_all.to_excel(file_path, index=False)
            with open(file_path, "rb") as f:
                st.download_button("📥 اضغط هنا لتحميل الملف", f, file_name="HSS_Report.xlsx")