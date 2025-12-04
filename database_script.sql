 CREATE TABLE users (
	id SERIAL PRIMARY KEY,
	username VARCHAR(255) NOT NULL,
	password VARCHAR(255) NOT NULL,
	role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'employee', 'client')),
	created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO users (username, password, role) VALUES ('admin', '$2b$12$idexu9pSkklLDq3EU21VguttiTfD31uEnppnqifXesiHkKIfXE1cy', 'admin');

CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    fullname VARCHAR(50),
    birth_date DATE NOT NULL,
    gender VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE parent (
	id SERIAL PRIMARY KEY,
	national_id VARCHAR(100),
	address VARCHAR(255),
	phone VARCHAR(30),
	parent_id INT REFERENCES users(id) ON DELETE CASCADE,
	child_id INT REFERENCES patients(id) ON DELETE CASCADE
);

CREATE TABLE vaccines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    disease VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE vaccine_schedule (
    id SERIAL PRIMARY KEY,
    vaccine_id INT REFERENCES vaccines(id) ON DELETE CASCADE,
    dose_number INT NOT NULL,
    age_months INT NOT NULL,   -- 0 = عند الولادة
    is_required BOOLEAN DEFAULT TRUE
);

CREATE TABLE patient_vaccines (
    id SERIAL PRIMARY KEY,
    patient_id INT REFERENCES patients(id) ON DELETE CASCADE,
    vaccine_id INT REFERENCES vaccines(id) ON DELETE CASCADE,
    dose_number INT NOT NULL,
    scheduled_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending / done / late
    done_date DATE,
    notes TEXT
);

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    patient_id INT REFERENCES patients(id) ON DELETE CASCADE,
    patient_vaccine_id INT REFERENCES patient_vaccines(id),
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    is_seen BOOLEAN DEFAULT FALSE
);

INSERT INTO vaccines (name, disease) VALUES
('BCG', 'Tuberculosis'),
('Polio (OPV)', 'Poliomyelitis'),
('Penta (DTP-HepB-Hib)', 'Diphtheria, Tetanus, Pertussis, Hepatitis B, Hib'),
('Pneumococcal (PCV)', 'Pneumococcal infections'),
('Rotavirus', 'Rotavirus diarrhea'),
('Measles / ROR', 'Measles, Mumps, Rubella'),
('DTP Booster', 'Diphtheria, Tetanus, Pertussis'),
('DT Booster', 'Diphtheria, Tetanus');


INSERT INTO vaccine_schedule (vaccine_id, dose_number, age_months) VALUES
-- Birth
(1, 0, 0),
(2, 0, 0),

-- 2 months
(3, 1, 2),
(2, 1, 2),
(4, 1, 2),
(5, 1, 2),

-- 3 months
(3, 2, 3),
(2, 2, 3),
(5, 2, 3),

-- 4 months
(3, 3, 4),
(2, 3, 4),
(4, 2, 4),

-- 11 months
(6, 1, 11),
(4, 3, 11),

-- 18 months
(7, 4, 18),
(2, 4, 18),
(6, 2, 18),

-- 6 years
(8, 5, 72),
(2, 5, 72);


INSERT INTO users (username, password, role) VALUES
('client', '$2b$12$idexu9pSkklLDq3EU21VguttiTfD31uEnppnqifXesiHkKIfXE1cy', 'client'),
('amira.khaled',   '$2b$12$idexu9pSkklLDq3EU21VguttiTfD31uEnppnqifXesiHkKIfXE1cy', 'client'),
('mohamed.nacer',  '$2b$12$idexu9pSkklLDq3EU21VguttiTfD31uEnppnqifXesiHkKIfXE1cy', 'client'),
('salima.faress',  '$2b$12$idexu9pSkklLDq3EU21VguttiTfD31uEnppnqifXesiHkKIfXE1cy', 'client');

INSERT INTO patients (fullname, birth_date, gender) VALUES
('أحمد بن علي', '2020-05-12', 'ذكر'),
('سارة خالد',   '2022-02-08', 'أنثى'),
('مروان ناصر',  '2019-11-30', 'ذكر'),
('لمياء فارس',  '2021-07-22', 'أنثى');

INSERT INTO parent (national_id, address, phone, parent_id, child_id) VALUES
('120345678912345678', 'الجزائر، الجزائر الوسطى',  '0550123456', 2, 1),
('130987654398765432', 'وهران، السانيا',           '0666543210', 3, 2),
('100112233445566778', 'سطيف، العلمة',            '0777011223', 4, 3),
('150556677889900112', 'باتنة، تازولت',           '0799123411', 5, 4);

INSERT INTO patient_vaccines 
(patient_id, vaccine_id, dose_number, scheduled_date, status, done_date, notes)
VALUES
(1, 1, 0, '2020-05-12', 'done', '2020-05-12', 'تم التطعيم عند الولادة'),
(1, 3, 1, '2020-07-12', 'done', '2020-07-15', 'جرعة شهرين'),
(1, 6, 1, '2021-04-12', 'late', NULL, 'جرعة 11 شهر — متأخرة'),
(1, 7, 4, '2025-01-12', 'pending', NULL, 'جرعة 18 شهر — موعد قادم');

INSERT INTO patient_vaccines VALUES
(DEFAULT, 2, 1, 3, '2022-02-08', 'done', '2022-02-08', 'جرعة الولادة'),
(DEFAULT, 2, 3, 1, '2022-04-08', 'done', '2022-04-10', 'جرعة 2 شهر'),
(DEFAULT, 2, 5, 1, '2023-01-08', 'done', '2023-01-10', 'جرعة 11 شهر');

INSERT INTO patient_vaccines 
(patient_id, vaccine_id, dose_number, scheduled_date, status)
VALUES
(3, 1, 0, '2019-11-30', 'done'),
(3, 3, 1, '2020-01-30', 'done'),
(3, 6, 1, '2020-10-30', 'late');  -- متأخر جدًا

INSERT INTO patient_vaccines 
(patient_id, vaccine_id, dose_number, scheduled_date, status)
VALUES
(4, 1, 0, '2021-07-22', 'done'),
(4, 3, 1, '2021-09-22', 'done'),
(4, 6, 1, '2022-06-22', 'pending'); -- موعد قادم

INSERT INTO notifications (patient_id, patient_vaccine_id, message, is_seen) VALUES
(1, 3, 'تذكير: موعد التطعيم متأخر لطفلك أحمد', FALSE),
(3, 2, 'تنبيه: التطعيم الخاص بمروان متأخر للغاية', FALSE),
(4, 1, 'لديك موعد تطعيم جديد لابنتك لمياء', TRUE);

INSERT INTO users (username, password, role) VALUES ('employee', '$2b$12$idexu9pSkklLDq3EU21VguttiTfD31uEnppnqifXesiHkKIfXE1cy', 'employee');
