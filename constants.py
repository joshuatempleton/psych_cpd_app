from __future__ import annotations

APP_TITLE = "Psychologist CPD Portfolio Tracker"
APP_VERSION = "3.2.3"

EVIDENCE_OPTIONS = [
    "Certificate of attendance/completion", "Receipt", "Reading list",
    "Professional association CPD record", "Degree certificate / academic transcript",
    "Assignment / thesis / research report / published article",
    "Supervision / mentoring plan or progress report", "Flyer / program / registration confirmation",
    "Self-recorded reflection only", "Other",
]

CPD_ACTIVITY_TYPES = ["Workshop", "Seminar", "Conference", "Reading", "Online course", "Webinar", "Teaching / presenting", "Research / writing", "Supervision-related training", "Other"]
PEER_FORMATS = ["Individual supervision", "Mentoring", "Consultation", "Group peer consultation", "Case discussion", "Peer support network", "Learning plan review", "Other"]

ENDORSEMENT_OPTIONS = [
    "Clinical neuropsychology", "Clinical psychology", "Community psychology",
    "Counselling psychology", "Educational and developmental psychology",
    "Forensic psychology", "Health psychology", "Organisational psychology",
    "Sport and exercise psychology",
]

REGISTRAR_REQUIREMENTS = {
    "Approved to seventh year or above, e.g. DPsych/PsyD": {"minimum_weeks": 44, "practice_hours": 1500, "supervision_hours": 40, "active_cpd_hours": 40},
    "Approved to sixth year with doctoral thesis, e.g. MPsych/PhD": {"minimum_weeks": 66, "practice_hours": 2250, "supervision_hours": 60, "active_cpd_hours": 60},
    "Approved sixth-year Masters pathway": {"minimum_weeks": 88, "practice_hours": 3000, "supervision_hours": 80, "active_cpd_hours": 80},
}

COMPETENCY_RATINGS = ["Not yet addressed", "Developing", "Consolidating", "Achieved", "Supervisor confirmed"]

GENERIC_ENDORSEMENT_COMPETENCIES = {
    "1. Knowledge of the discipline": ["Area-specific knowledge of psychological theories, models and evidence"],
    "2. Ethical, legal and professional matters": ["Area-specific ethical, legal and professional matters"],
    "3. Psychological assessment and measurement": ["Area-specific assessment and measurement"],
    "4. Intervention strategies": ["Area-specific intervention strategies"],
    "5. Research and evaluation": ["Area-specific research and evaluation"],
    "6. Communication and interpersonal relationships": ["Area-specific communication and interpersonal relationships"],
    "7. Working with people from diverse groups": ["Area-specific work with diverse groups"],
    "8. Practice across the lifespan": ["Area-specific lifespan practice"],
}

ENDORSEMENT_COMPETENCIES = {
    "Organisational psychology": {
        "1. Knowledge of the discipline": [
            "Broad understanding of psychological theory as it pertains to successful functioning of organisations",
            "Understanding the role of behavioural factors in organisational effectiveness and employee satisfaction, productivity, safety and wellbeing",
            "Understanding the social, political and economic context determining organisational workplace design and the role of psychological factors",
            "Knowledge of industrial, organisational and occupational psychology; personnel and vocational psychology; HR management and development; human factors; coaching psychology; consumer psychology",
        ],
        "2. Ethical, legal and professional matters": [
            "Understanding ethical issues in organisational settings and how to manage them",
            "Communicating organisational psychologist ethical obligations to others",
            "Ethical and professional use of psychological tests, including reliability, validity, qualifications, test security and online/multinational testing risks",
        ],
        "3. Psychological assessment and measurement": [
            "Use of multi-source and multi-rater assessments relevant to organisational effectiveness",
            "Use of targeted validated measures including job analysis, recruitment and selection, worker motivation, work performance, health and wellbeing, and career development",
            "Use of multiple methods of evaluating health status, including diagnostic classification systems and relevant assessment scales",
        ],
        "4. Intervention strategies": [
            "Individual psychological interventions including coaching, counselling, transitions, loss, personal difficulties and work attitudes",
            "Group interventions including team facilitation, leadership, change management, strategic planning and conflict resolution",
            "Whole-system interventions including incentive and motivation strategies, performance management systems and organisational policy/training programs",
        ],
        "5. Research and evaluation": [
            "Identification of psychological questions from organisational design and needs analyses",
            "Communication of research methods and findings to non-psychologists in organisational settings",
            "Transformation of research and evaluation findings into strategic policies for managers and leaders",
        ],
        "6. Communication and interpersonal relationships": [
            "Communicating psychological factors relevant to organisations to senior executives, leaders/managers, employees and the public",
            "Providing consultancy advice about psychological matters relevant to organisations",
            "Communicating obligations of organisational psychologists in different roles and settings",
            "Understanding psychologist roles within business and organisational systems and communicating effectively orally and in writing",
        ],
        "7. Working with people from diverse groups": [
            "Applying knowledge of how organisational psychology is influenced by social, historical, professional and cultural contexts",
            "Practising competently and ethically with people from diverse backgrounds",
            "Sensitivity and knowledge of working with Aboriginal and Torres Strait Islander peoples",
        ],
        "8. Practice across the lifespan": ["Competence across childhood, adolescence, adulthood and late adulthood as relevant to organisational psychology work"],
    }
}

def get_competency_map(area: str) -> dict[str, list[str]]:
    return ENDORSEMENT_COMPETENCIES.get(area, GENERIC_ENDORSEMENT_COMPETENCIES)
