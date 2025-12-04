-- Add missing foreign key constraint
ALTER TABLE parent 
ADD CONSTRAINT fk_parent_child 
FOREIGN KEY (child_id) 
REFERENCES patients(id) 
ON DELETE CASCADE;

-- Add CHECK constraint for status
ALTER TABLE patient_vaccines
ADD CONSTRAINT chk_status 
CHECK (status IN ('pending', 'done', 'late'));

-- Update notifications table to CASCADE on delete
ALTER TABLE notifications
DROP CONSTRAINT IF EXISTS notifications_patient_vaccine_id_fkey,
ADD CONSTRAINT notifications_patient_vaccine_id_fkey 
FOREIGN KEY (patient_vaccine_id) 
REFERENCES patient_vaccines(id) 
ON DELETE CASCADE;
