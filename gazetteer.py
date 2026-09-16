"""
Gazetteer de habilidades por sector.
Estructura: { "categoria": ["habilidad 1", "habilidad 2", ...] }
Cada entrada se normaliza a minúsculas al cargarse; el matcher de spaCy
se encarga de encontrar coincidencias sin importar mayúsculas/minúsculas.

Este es un punto de partida. Conviene revisarlo contra los CVs reales
y ampliarlo con los términos específicos que aparezcan y no estén
cubiertos (sobre todo variantes y siglas propias del contexto peruano).
"""

GAZETTEER = {
    "tecnologia": [
        "python", "java", "javascript", "typescript", "sql", "nosql",
        "power bi", "tableau", "excel avanzado", "machine learning",
        "inteligencia artificial", "procesamiento de lenguaje natural",
        "análisis de datos", "ciencia de datos", "bases de datos",
        "administración de bases de datos", "gestión de bases de datos",
        "desarrollo web", "desarrollo de software", "react", "node.js",
        "aws", "azure", "google cloud", "cloud computing", "docker", "kubernetes",
        "metodologías ágiles", "scrum", "scrum master", "devops", "ciberseguridad",
        "redes", "soporte técnico", "sistemas operativos",
        "control de versiones", "git", "api rest", "restful", "openapi",
        "uml", "bpmn", "bizagi", "rup", "itil",
        "sql server", "postgres", "postgresql", "oracle", "pl/sql",
        "spring", "hibernate", "jpa", "junit", "jsp", "jquery",
        "maven", "selenium", ".net", "genexus", "visual foxpro",
        "sap", "erp", "jasper reports", "apache tomcat", "weblogic",
        "figma", "postman", "visual studio code", "enterprise architect",
        "gestión de riesgos", "gestión de cambios", "control de calidad",
        "aseguramiento de la calidad", "qa", "prompt engineering",
        "pytorch", "tensorflow", "llm", "llms", "langchain", "computer vision",
        "nlp", "siem", "splunk", "incident response", "firewalls",
        "apache spark", "airflow", "snowflake", "microservicios",
        "kanban", "jira", "facilitación ágil", "terraform", "ansible",
        "jenkins", "linux", "bash", "ms project",
    ],
    "salud": [
        "atención al paciente", "enfermería", "farmacología",
        "primeros auxilios", "cuidados intensivos", "terapia física",
        "nutrición clínica", "salud pública", "epidemiología",
        "historia clínica", "gestión hospitalaria", "bioseguridad",
        "diagnóstico clínico", "administración de medicamentos",
        "psicología clínica", "trabajo social", "telemedicina",
        "ecocardiografía", "unidad coronaria", "cateterismo",
        "electrocardiografía", "composición corporal", "nutrición entérica",
        "psicofarmacología", "dsm-5", "cirugía laparoscópica", "urgencias",
        "soporte vital avanzado", "acls", "farmacovigilancia",
        "ensayos clínicos",
    ],
    "administracion_gestion": [
        "gestión de proyectos", "gestión pública", "gestión del talento",
        "planificación estratégica", "presupuesto público",
        "contrataciones del estado", "control interno",
        "gestión de procesos", "mejora continua", "auditoría",
        "contabilidad", "finanzas corporativas", "recursos humanos",
        "logística", "cadena de suministro", "supply chain management",
        "gestión documentaria", "gestión de compras", "gestión de inventarios",
        "gestión de abastecimiento", "planeamiento de proyectos",
        "atención al ciudadano", "liderazgo de equipos", "gerencia de operaciones",
        "niif", "sap s/4hana", "impuestos", "sap mm", "gestión de proveedores",
        "modelado financiero", "reclutamiento", "desarrollo organizacional",
        "sap scm",
    ],
    "ventas_marketing": [
        "ventas b2b", "ventas b2c", "negociación", "atención al cliente",
        "marketing digital", "redes sociales", "seo", "sem",
        "gestión de marca", "crm", "prospección de clientes",
        "cierre de ventas", "telemarketing", "comercio exterior",
        "análisis de mercado", "plan de marketing", "e-commerce",
    ],
    "educacion": [
        "docencia", "diseño curricular", "evaluación educativa",
        "tutoría", "educación virtual", "andragogía",
        "planificación de sesiones de aprendizaje",
    ],
    "idiomas": [
        "inglés", "inglés avanzado", "inglés intermedio", "inglés básico",
        "portugués", "francés", "quechua",
    ],
    "habilidades_blandas": [
        "trabajo en equipo", "comunicación efectiva", "resolución de problemas",
        "pensamiento crítico", "adaptabilidad", "proactividad",
        "orientación a resultados", "toma de decisiones",
    ],
}

def gazetteer_flat():
    """Devuelve la lista completa de términos, sin categoría, en minúsculas."""
    terms = []
    for categoria, items in GAZETTEER.items():
        terms.extend([t.lower() for t in items])
    return sorted(set(terms))

def gazetteer_size_by_category():
    return {cat: len(items) for cat, items in GAZETTEER.items()}

if __name__ == "__main__":
    print("Categorías y cantidad de términos:")
    for cat, n in gazetteer_size_by_category().items():
        print(f"  {cat}: {n}")
    print(f"\nTotal de términos únicos: {len(gazetteer_flat())}")
