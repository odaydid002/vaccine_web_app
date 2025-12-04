#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
نظام إدارة التطعيمات - ملف التحقق من الصحة
Vaccination Management System - Health Check File
"""

import os
import sys

def check_project_structure():
    """التحقق من بنية المشروع"""
    print("🔍 جاري التحقق من بنية المشروع...")
    
    required_files = [
        'app.py',
        'config.py',
        'requirements.txt',
        'templates/main.html',
        'templates/parent_detail.html',
        'templates/admin.html',
        'templates/login.html',
        'templates/client.html',
        'static/css/main.css',
        'static/css/admin.css',
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ الملفات المفقودة:")
        for f in missing_files:
            print(f"   - {f}")
        return False
    else:
        print("✅ جميع الملفات الأساسية موجودة")
        return True

def check_python_version():
    """التحقق من إصدار Python"""
    print("\n🔍 جاري التحقق من إصدار Python...")
    
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor} (جيد)")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor} (يتطلب 3.8+)")
        return False

def check_requirements():
    """التحقق من المكتبات المطلوبة"""
    print("\n🔍 جاري التحقق من المكتبات المطلوبة...")
    
    required_packages = {
        'flask': 'Flask',
        'psycopg2': 'psycopg2-binary',
        'bcrypt': 'bcrypt',
        'werkzeug': 'werkzeug'
    }
    
    missing = []
    installed = []
    
    for module, package_name in required_packages.items():
        try:
            __import__(module)
            installed.append(package_name)
        except ImportError:
            missing.append(package_name)
    
    if installed:
        print("✅ المكتبات المثبتة:")
        for pkg in installed:
            print(f"   - {pkg}")
    
    if missing:
        print("\n❌ المكتبات الناقصة:")
        for pkg in missing:
            print(f"   - {pkg}")
        print("\nقم بتثبيت المكتبات الناقصة:")
        print(f"pip install {' '.join(missing)}")
        return False
    else:
        print("\n✅ جميع المكتبات المطلوبة مثبتة")
        return True

def check_database_config():
    """التحقق من إعدادات قاعدة البيانات"""
    print("\n🔍 جاري التحقق من إعدادات قاعدة البيانات...")
    
    try:
        from config import DB_CONFIG
        print("✅ ملف الإعدادات موجود")
        
        required_keys = ['dbname', 'user', 'password', 'host', 'port']
        config_ok = True
        
        for key in required_keys:
            if key in DB_CONFIG:
                value = DB_CONFIG[key]
                if value:
                    print(f"   ✅ {key}: محدد")
                else:
                    print(f"   ⚠️  {key}: فارغ")
                    config_ok = False
            else:
                print(f"   ❌ {key}: مفقود")
                config_ok = False
        
        return config_ok
        
    except ImportError:
        print("❌ ملف الإعدادات غير موجود")
        return False

def check_database_connection():
    """التحقق من الاتصال بقاعدة البيانات"""
    print("\n🔍 جاري التحقق من الاتصال بقاعدة البيانات...")
    
    try:
        import psycopg2
        from config import DB_CONFIG
        
        conn = psycopg2.connect(
            dbname=DB_CONFIG['dbname'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port']
        )
        
        cursor = conn.cursor()
        
        # التحقق من الجداول الأساسية
        required_tables = [
            'users',
            'patients',
            'parent',
            'vaccines',
            'patient_vaccines',
            'vaccine_schedule',
            'notifications'
        ]
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public'
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        print("✅ الاتصال بقاعدة البيانات نجح")
        print("\nالجداول المتوفرة:")
        
        all_exist = True
        for table in required_tables:
            if table in existing_tables:
                print(f"   ✅ {table}")
            else:
                print(f"   ❌ {table} (مفقود)")
                all_exist = False
        
        cursor.close()
        conn.close()
        
        return all_exist
        
    except Exception as e:
        print(f"❌ فشل الاتصال: {str(e)}")
        return False

def check_templates():
    """التحقق من ملفات النماذج"""
    print("\n🔍 جاري التحقق من ملفات النماذج...")
    
    templates = {
        'templates/main.html': 'صفحة الموظف',
        'templates/parent_detail.html': 'تفاصيل الولي',
        'templates/admin.html': 'لوحة الإدارة',
        'templates/login.html': 'صفحة تسجيل الدخول',
    }
    
    all_exist = True
    for template, description in templates.items():
        if os.path.exists(template):
            size = os.path.getsize(template)
            print(f"   ✅ {description} ({size} bytes)")
        else:
            print(f"   ❌ {description} - مفقود")
            all_exist = False
    
    return all_exist

def main():
    """تشغيل جميع الفحوصات"""
    print("="*50)
    print("🏥 نظام إدارة التطعيمات")
    print("ملف التحقق من الصحة")
    print("="*50 + "\n")
    
    checks = [
        ("بنية المشروع", check_project_structure),
        ("إصدار Python", check_python_version),
        ("المكتبات المطلوبة", check_requirements),
        ("ملفات النماذج", check_templates),
        ("إعدادات قاعدة البيانات", check_database_config),
        ("الاتصال بقاعدة البيانات", check_database_connection),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ خطأ أثناء {check_name}: {str(e)}")
            results.append((check_name, False))
    
    # ملخص النتائج
    print("\n" + "="*50)
    print("📊 ملخص النتائج")
    print("="*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ نجح" if result else "❌ فشل"
        print(f"{status:8} - {check_name}")
    
    print(f"\n{'='*50}")
    print(f"النتيجة: {passed}/{total} فحوصات نجحت")
    
    if passed == total:
        print("🎉 تم! النظام جاهز للتشغيل!")
        print("\nلتشغيل النظام:")
        print("  python app.py")
        return True
    else:
        print("⚠️  يوجد مشاكل تحتاج إلى إصلاح قبل التشغيل")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
