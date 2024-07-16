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

# Access policies for hospital C's overall router
ORG_POLICIES = [
    {
        "uid": "1",
        "description": "Only requesters part of hospital A or C can access hospital C records",
        "effect": "allow",
        "rules": {
            "subject": {"$.org": {"condition": "IsIn", "values": ["A", "C"]}},
            "resource": {},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    }
]

C_GATE_POLICY = [
    {
        "uid": "1",
        "description": "Physicians, nurses, technicians, and researchers at hospital C can access records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "Equals", "value": "C"},
                        "$.role": {"condition": "IsIn", "values": ["physician", "nurse", "technician", "researcher"]},
                       },
            "resource": {},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    },
    {
        "uid": "2",
        "description": "Physicians at hospital A affiliated with C_neuro can access records",
        "effect": "allow",
        "rules": {
            "subject": {
                        "$.org": {"condition": "Equals", "value": "A"},
                        "$.role": {"condition": "Equals", "value": "physician"},
                        "$.affiliations": {"condition": "AnyIn", "values": ["C_neuro"]}, # i.e. if contains
                       },
            "resource": {},
            "action": [{"$.method": {"condition": "Equals", "value": "read"}}],
            "context": {}
        },
        "targets": {},
        "priority": 0
    },
]

########################################################################################
########################################################################################
########################################################################################

# Access policies for hospital C's department leaves
DEPT_GATE_POLICIES = {
    "admissions": C_GATE_POLICY,
    "neurology": C_GATE_POLICY,
}

# Access policies for hospital C's department leaves, final check
# TODO use allow everything policy as a placeholder for more fine-grained document access policies
DEPT_POLICIES = {
    "admissions": ALLOW_ALL,
    "neurology": ALLOW_ALL,
}
