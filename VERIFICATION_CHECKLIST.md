# تحقق شامل من نموذج إضافة المريض الجديد
## Complete Verification of Add Patient Form

---

## ✅ المرحلة الأولى: بيانات الولي (Step 1: Parent Information)

### الحقول المطلوبة (Required Fields):
- ✅ **الاسم الأول للولي** (Parent First Name)
  - Field name: `pt-fname`
  - Type: Text (required)
  - Saved as: First part of user account username
  - DB Table: `users` (username column)

- ✅ **اللقب** (Parent Last Name)
  - Field name: `pt-lname`
  - Type: Text (required)
  - Saved as: Second part of user account username
  - DB Table: `users` (username = "fname.lname")

### الحقول الإضافية (Additional Fields):

- ✅ **رقم التعريف الوطني** (National ID - 18 digits)
  - Field name: `p-national-id`
  - Type: Text
  - Validation: 18-digit number
  - Auto-saved as: Password (hashed with bcrypt)
  - DB Table: `parent` (national_id column)
  - Status: Required for local parents, disabled when foreign parent is selected

- ✅ **رقم جواز السفر** (Passport Number - for foreigners)
  - Field name: `p-passport`
  - Type: Text
  - Status: Disabled by default, enabled when "foreign parent" checkbox is checked
  - Auto-saved as: Password (if national ID not provided)
  - DB Table: `parent` (passport_number column)
  - NEW FEATURE: Added in latest update

- ✅ **رقم الهاتف** (Phone Number)
  - Field name: `p-phone`
  - Type: Tel (required)
  - DB Table: `parent` (phone column)

- ✅ **العنوان** (Address)
  - Field name: `p-address`
  - Type: Text
  - DB Table: `parent` (address column)

- ✅ **الدفتر العائلي** (Family Booklet Declaration)
  - Field name: `p-family-booklet`
  - Type: Checkbox
  - Options: معلّن (declared) / غير معلّن (not declared)
  - DB Table: `parent` (family_booklet_declared column)
  - Values: TRUE = معلّن, FALSE = غير معلّن

- ✅ **الولي أجنبي** (Foreign Parent Checkbox)
  - Field name: `p-is-foreign`
  - Type: Checkbox
  - Behavior: 
    - When UNCHECKED: National ID required, Passport disabled
    - When CHECKED: National ID disabled, Passport required
  - Automatically handled by `toggleForeignParent()` function

### بيانات إضافية مرتبطة (Auto-saved Related Data):
- ✅ **اسم المستخدم** (Username): Automatically generated as `fname.lname`
- ✅ **كلمة السر** (Password): Automatically generated as hashed national ID (or passport for foreigners)
- ✅ **Role**: Automatically set to "client"
- ✅ **Created By**: Automatically recorded as current employee ID
- ✅ **Created At**: Automatically recorded with timestamp

---

## ✅ المرحلة الثانية: بيانات المولود (Step 2: Newborn Information)

### الحقول المطلوبة (Required Fields):

- ✅ **اسم المولود الأول** (Newborn First Name)
  - Field name: `p-first`
  - Type: Text (required)
  - Saved in: `patients` table (fullname column, combined with last name)

- ✅ **لقب المولود** (Newborn Last Name)
  - Field name: `p-last`
  - Type: Text
  - Saved in: `patients` table (fullname column, combined with first name)

- ✅ **جنس المولود** (Newborn Gender)
  - Field name: `p-gender`
  - Type: Select dropdown (required)
  - Options: ذكر (Male), أنثى (Female)
  - DB Table: `patients` (gender column)

- ✅ **تاريخ الميلاد** (Birth Date)
  - Field name: `p-birth`
  - Type: Date (required)
  - DB Table: `patients` (birth_date column)

### الحقول الإضافية (Additional Fields):

- ✅ **مكان الميلاد** (Birth Place)
  - Field name: `p-birthplace`
  - Type: Text
  - DB Table: `patients` (birthplace column)

- ✅ **وزن المولود** (Newborn Weight)
  - Field name: `p-weight`
  - Type: Number (decimal, step 0.1)
  - Unit: كجم (kg)
  - DB Table: `patients` (weight_kg column)
  - **Real-time Status Indicator**:
    - If weight < 2 kg: Shows "نقص الوزن" (Underweight) in RED (#f44336)
    - If weight ≥ 2 kg: Shows "طبيعي" (Normal) in GREEN (#4caf50)
    - Updates automatically as user types

- ✅ **حالة الأم** (Maternal Health Status)
  - Field name: `maternal-health`
  - Type: Select dropdown
  - Options: 
    - جيدة (Good)
    - متوسطة (Fair)
    - مقلقة (Concerning)
  - Default: جيدة (Good)
  - DB Table: `patients` (maternal_health column)

- ✅ **حالة طارئة** (Emergency Case)
  - Field name: `p-emergency`
  - Type: Checkbox
  - DB Table: `patients` (emergency_flag column)
  - Values: TRUE (checked), FALSE (unchecked)

- ✅ **ملاحظات الحالة الطارئة** (Emergency Case Notes)
  - Field name: `p-emergency-note`
  - Type: Textarea (min-height: 100px)
  - DB Table: `patients` (emergency_note column)
  - Status: Enabled regardless of emergency checkbox

---

## ✅ المرحلة الثالثة: المستندات واللقاحات (Step 3: Documents & Vaccines)

### شهادة الميلاد (Birth Certificate):

- ✅ **شهادة بيان الولادة** (Birth Certificate)
  - Field name: `birth_certificate`
  - Type: File upload
  - Accepted formats: PDF, JPG, JPEG, PNG
  - Storage: Uploaded to `static/uploads/` folder
  - Filename pattern: `{patient_id}_{timestamp}_{original_filename}`
  - DB Table: `patients` (birth_certificate column - stores file path)

### اللقاحات (Vaccines):

- ✅ **قائمة اللقاحات المتاحة** (Available Vaccines List)
  - Dynamically populated from database `vaccines` table
  - Each vaccine has:
    - **Checkbox for selection**: name=`vaccines`, value=`{vaccine_id}`
    - **Checkbox for "تم الإعطاء" (Given)**: name=`given_{vaccine_id}`
  - Scrollable list (max-height: 300px)
  - Visual styling: Items displayed with vaccine names and status

- ✅ **خيار التأكيد عند الحقنة** (Confirm Vaccine Given)
  - Field pattern: `given_{vaccine_id}`
  - Type: Checkbox
  - Behavior: 
    - If checked: Record vaccine as `status='done'` with today's date
    - If unchecked: Record vaccine as `status='pending'` with scheduled date
  - DB Table: `patient_vaccines` (status, done_date columns)

---

## 🗄️ قاعدة البيانات (Database Storage)

### جدول `users` (User Accounts):
| Column | Value | Source |
|--------|-------|--------|
| username | fname.lname | Auto-generated from pt-fname + pt-lname |
| password | hashed(nationalId or passport) | Auto-hashed using bcrypt |
| role | "client" | Auto-set |

### جدول `parent` (Parent/Guardian):
| Column | Source | Required |
|--------|--------|----------|
| national_id | p-national-id | For locals only |
| passport_number | p-passport | For foreigners only (NEW) |
| phone | p-phone | ✅ Required |
| address | p-address | Optional |
| family_booklet_declared | p-family-booklet (checkbox) | Optional |
| parent_id | users.id | Auto-linked |
| created_by | session.user_id | Auto-saved |
| created_at | NOW() | Auto-timestamp |

### جدول `patients` (Newborn/Child):
| Column | Source | Required |
|--------|--------|----------|
| fullname | p-first + p-last | ✅ Required |
| birth_date | p-birth | ✅ Required |
| gender | p-gender | ✅ Required |
| birthplace | p-birthplace | Optional |
| weight_kg | p-weight | Optional (with real-time validation) |
| maternal_health | maternal-health | Optional |
| emergency_flag | p-emergency | Optional |
| emergency_note | p-emergency-note | Optional |
| birth_certificate | birth_certificate (file) | Optional |
| created_by | session.user_id | Auto-saved |
| created_at | NOW() | Auto-timestamp |

### جدول `patient_vaccines` (Vaccine Records):
| Column | Source | Notes |
|--------|--------|-------|
| patient_id | Automatically linked | Auto |
| vaccine_id | vaccines (selected) | From checkboxes |
| dose_number | vaccine_schedule | Auto |
| status | given_{vaccine_id} checkbox | done / pending |
| done_date | p-birth (if given) | Set to birth date if given |
| scheduled_date | calculated from schedule | Auto-calculated |
| created_by | session.user_id | Auto-saved |
| created_at | NOW() | Auto-timestamp |

---

## 🔐 الأمان والتحقق (Security & Validation)

### Password Generation (كلمة السر):
1. If **National ID** provided → Use as password (hashed)
2. Else if **Passport** provided → Use as password (hashed)
3. Else → Generate random UUID

### National ID Validation:
- Expected format: 18 digits
- Auto-saved as encrypted password
- Required for local parents
- Disabled when foreign parent checkbox is checked

### Foreign Parent Handling:
- National ID field becomes disabled and optional
- Passport field becomes enabled and required
- Password generation uses passport number if available
- Allows registration of parents without national ID

---

## ✅ JavaScript 功能 (JavaScript Functions)

### toggleForeignParent(checkbox):
Handles the conditional display/requirement of National ID vs Passport fields
- When checked: National ID disabled, Passport required
- When unchecked: National ID required, Passport disabled
- Updates helper text dynamically

### updateWeightStatus():
Real-time weight validation and feedback
- Input: Weight in kg
- Output: Status message + color
  - < 2 kg: "نقص الوزن" (RED)
  - ≥ 2 kg: "طبيعي" (GREEN)

### Form Navigation:
- `nextStep()`: Move to next form section
- `prevStep()`: Move to previous form section
- `updateStepUI()`: Update stepper indicators and buttons
- `openAddModal()`: Open the modal dialog
- `closeAddModal()`: Close and reset the form

---

## 📋 ملخص التحقق (Verification Summary)

### ✅ تم التحقق من:
1. ✅ جميع الحقول المطلوبة موجودة
2. ✅ جميع الحقول الإضافية موجودة
3. ✅ الحفظ التلقائي لاسم المستخدم وكلمة السر
4. ✅ التحقق من وزن المولود (نقص الوزن vs طبيعي)
5. ✅ خيار الدفتر العائلي (معلّن vs غير معلّن)
6. ✅ دعم الآباء الأجانب مع رقم جواز السفر
7. ✅ رفع شهادة بيان الولادة
8. ✅ قائمة اللقاحات مع خيار التأكيد
9. ✅ حالة طارئة مع ملاحظات
10. ✅ تتبع من قام بإنشاء السجل (created_by)
11. ✅ جميع البيانات محفوظة في قاعدة البيانات بشكل صحيح

### 🆕 الميزات الجديدة:
- ✨ حقل رقم جواز السفر للأجانب
- ✨ Conditional field display based on foreign parent status
- ✨ تسجيل created_by في جدول parent
- ✨ دعم كامل لكل من الوطنيين والأجانب

---

**Status**: ✅ **جميع المتطلبات موجودة وتعمل بشكل صحيح**
**Last Updated**: December 5, 2025
**Database Migration**: passport_number column added to parent table
