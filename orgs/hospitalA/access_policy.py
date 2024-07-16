import os
import sys 
sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

ALLOW_ALL = [
    {
        "uid": "1",
        "description": "Everybody can access all records",
        "effect": "allow",
        "rules": {
            "subject": {},
            "resource": {},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    }
]

########################################################################################
########################################################################################
########################################################################################

# Access policies for hospital A's overall router
ORG_POLICIES = [
    {
        "uid": "1",
        "description": "Only requesters part of hospital A and hospital B can access hospital A records",
        "effect": "allow",
        "rules": {
            "subject": {"$.org": {"condition": "IsIn", "values": ["A", "B"]}},
            "resource": {},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    }
]

########################################################################################
########################################################################################
########################################################################################

ADMISSIONS_POLICIES = [
        {
        "uid": "1",
        "description": "Physicians, nurses, and administrative staff at hospital A can access admissions records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "Equals", "value": "A"},
                        "$.role": {"condition": "IsIn", "values": ["physician", "nurse", "admin"]},
                       },
            "resource": {"$.dept_id": {"condition": "Equals", "value": "admissions"}},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    },
    {
        "uid": "2",
        "description": "Physicians and nurses at hospital B can access admissions records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "Equals", "value": "B"},
                        "$.role": {"condition": "IsIn", "values": ["physician", "nurse"]},
                       },
            "resource": {"$.dept_id": {"condition": "Equals", "value": "admissions"}},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    },
]

MEDICINE_POLICIES = [
    {
        "uid": "1",
        "description": "Physicians and nurses at hospital A can access medicine records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "Equals", "value": "A"},
                        "$.role": {"condition": "IsIn", "values": ["physician", "nurse"]},
                       },
            "resource": {"$.dept_id": {"condition": "Equals", "value": "medicine"}},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    },
    {
        "uid": "2",
        "description": "Physicians at hospital B can access medicine records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "Equals", "value": "B"},
                        "$.role": {"condition": "Equals", "value": "physician"},
                       },
            "resource": {"$.dept_id": {"condition": "Equals", "value": "medicine"}},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    },
]

ORTHOPAEDICS_POLICIES = [
    {
        "uid": "1",
        "description": "Physicians and nurses at hospital A can access orthopedics records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "Equals", "value": "A"},
                        "$.role": {"condition": "IsIn", "values": ["physician", "nurse"]},
                       },
            "resource": {"$.dept_id": {"condition": "Equals", "value": "orthopaedics"}},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    },
    {
        "uid": "2",
        "description": "Radiology technicians at hospital A can access orthopedics records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "Equals", "value": "A"},
                        "$.role": {"condition": "Equals", "value": "technician"},
                        "$.dept": {"condition": "Equals", "value": "radiology"}
                       },
            "resource": {"$.dept_id": {"condition": "Equals", "value": "orthopaedics"}},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    },
    {
        "uid": "3",
        "description": "Physicians at hospital B can access orthopedics records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "Equals", "value": "B"},
                        "$.role": {"condition": "Equals", "value": "physician"}
                       },
            "resource": {"$.dept_id": {"condition": "Equals", "value": "orthopaedics"}},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    },
]

PSYCHIATRY_POLICIES = [
    {
        "uid": "1",
        "description": "Physicians, nurses, and psychologists at hospital A can access psychiatry records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "Equals", "value": "A"},
                        "$.role": {"condition": "IsIn", "values": ["physician", "nurse", "psychologist"]},
                       },
            "resource": {"$.dept_id": {"condition": "Equals", "value": "psychiatry"}},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    },
    {
        "uid": "2",
        "description": "Psychiatric technicians at hospital A can access psychiatry records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "Equals", "value": "A"},
                        "$.role": {"condition": "Equals", "value": "technician"},
                        "$.dept": {"condition": "Equals", "value": "psychiatry"}
                        },
            "resource": {"$.dept_id": {"condition": "Equals", "value": "psychiatry"}},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    },
    {
        "uid": "3",
        "description": "Physicians at hospital B can access psychiatry records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "Equals", "value": "B"},
                        "$.role": {"condition": "Equals", "value": "physician"}
                       },
            "resource": {"$.dept_id": {"condition": "Equals", "value": "psychiatry"}},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    },
]

SURGERY_POLICIES = [
    {
        "uid": "1",
        "description": "Physicians and nurses at hospital A can access surgery records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "Equals", "value": "A"},
                        "$.role": {"condition": "IsIn", "values": ["physician", "nurse"]},
                       },
            "resource": {"$.dept_id": {"condition": "Equals", "value": "surgery"}},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    },
    {
        "uid": "2",
        "description": "Physicians at hospital B can access surgery records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "Equals", "value": "B"},
                        "$.role": {"condition": "Equals", "value": "physician"}
                       },
            "resource": {"$.dept_id": {"condition": "Equals", "value": "surgery"}},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    },
]

# Access policies for hospital A's department leaves
DEPT_GATE_POLICIES = {
    "admissions": ADMISSIONS_POLICIES,
    "medicine": MEDICINE_POLICIES,
    "psychiatry": PSYCHIATRY_POLICIES,
    "orthopaedics": ORTHOPAEDICS_POLICIES,
    "surgery": SURGERY_POLICIES,
}

# Access policies for hospital A's department leaves, final check
# TODO use allow everything policy as a placeholder for more fine-grained document access policies
DEPT_POLICIES = {
    "admissions": ALLOW_ALL,
    "medicine": ALLOW_ALL,
    "psychiatry": ALLOW_ALL,
    "orthopaedics": ALLOW_ALL,
    "surgery": ALLOW_ALL,
}
