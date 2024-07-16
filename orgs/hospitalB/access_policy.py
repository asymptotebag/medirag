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
        "description": "Only requesters part of hospital A and hospital B can access hospital B records",
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
        "description": "Physicians, nurses, and administrative staff at hospital B can access admissions records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "Equals", "value": "B"},
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
        "description": "Physicians and nurses at hospital A can access admissions records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "Equals", "value": "A"},
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

CARDIOLOGY_POLICIES = [
    {
        "uid": "1",
        "description": "Physicians and nurses at hospitals A and B can access cardiology records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "IsIn", "values": ["A", "B"]},
                        "$.role": {"condition": "IsIn", "values": ["physician", "nurse"]},
                       },
            "resource": {"$.dept_id": {"condition": "Equals", "value": "cardiology"}},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    }
]

MEDICINE_POLICIES = [
    {
        "uid": "1",
        "description": "Physicians and nurses at hospital A and B can access medicine records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "IsIn", "values": ["A", "B"]},
                        "$.role": {"condition": "IsIn", "values": ["physician", "nurse"]},
                       },
            "resource": {"$.dept_id": {"condition": "Equals", "value": "medicine"}},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    }
]

# Access policies for hospital A's department leaves
DEPT_GATE_POLICIES = {
    "admissions": ADMISSIONS_POLICIES,
    "medicine": MEDICINE_POLICIES,
    "cardiology": CARDIOLOGY_POLICIES
}

# Access policies for hospital A's department leaves, final check
# TODO use allow everything policy as a placeholder for more fine-grained document access policies
DEPT_POLICIES = {
    "admissions": ALLOW_ALL,
    "medicine": ALLOW_ALL,
    "cardiology": ALLOW_ALL
}
