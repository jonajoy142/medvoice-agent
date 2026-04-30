"""
In-memory mock database for MedVoice AI demo
"""

# Patient data
patients = {
    "411326": {
        "name": "Jonah Carlisle",
        "history": ["eczema", "skin allergy"],
        "phone": "+1-555-0123",
        "email": "jonah.carlisle@email.com"
    },
    "411327": {
        "name": "Sarah Johnson",
        "history": ["acne", "dry skin"],
        "phone": "+1-555-0124",
        "email": "sarah.johnson@email.com"
    }
}

# Doctor data
doctors = {
    "dermatologist": [
        {
            "name": "Meera",
            "specialization": "Dermatology",
            "slots": ["10:00", "11:00", "14:00", "15:00"],
            "available_days": ["Monday", "Wednesday", "Friday"]
        },
        {
            "name": "Kumar",
            "specialization": "Dermatology", 
            "slots": ["09:00", "10:00", "13:00", "16:00"],
            "available_days": ["Tuesday", "Thursday"]
        }
    ],
    "general": [
        {
            "name": "Smith",
            "specialization": "General Practice",
            "slots": ["08:00", "09:00", "11:00", "14:00"],
            "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        }
    ]
}

# Appointments storage
appointments = []

# Session storage for active conversations
sessions = {}

def get_patient(opid):
    """Get patient by OPID"""
    return patients.get(opid)

def get_all_patients():
    """Get all patients"""
    return patients

def get_doctors(specialization=None):
    """Get doctors by specialization or all doctors"""
    if specialization:
        return doctors.get(specialization, [])
    return doctors

def add_appointment(appointment_data):
    """Add a new appointment"""
    appointment_data["id"] = len(appointments) + 1
    appointments.append(appointment_data)
    return appointment_data

def get_appointments():
    """Get all appointments"""
    return appointments

def get_appointments_by_patient(opid):
    """Get appointments for a specific patient"""
    return [apt for apt in appointments if apt.get("patient_opid") == opid]

def create_session(session_id):
    """Create a new session"""
    session_data = {
        "conversation": [],
        "opid": None,
        "patient_name": None,
        "selected_doctor": None,
        "last_doctor_list": [],
        "created_at": None
    }
    sessions[session_id] = session_data
    return session_data

def get_session(session_id):
    """Get session by ID"""
    return sessions.get(session_id)

def update_session(session_id, data):
    """Update session data"""
    if session_id in sessions:
        sessions[session_id].update(data)
    return sessions.get(session_id)
