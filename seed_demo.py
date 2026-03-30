"""Seed a demo course for local development and UI testing.

Creates a course with a hard-coded knowledge graph and a set of realistic
student trajectories — including both pending and approved hints — so that
the full instructor/student hint-approval flow can be exercised without
needing to upload a real PDF or run a live LLM session.

Usage
-----
    uv run python seed_demo.py -i professor@uni.edu
    uv run python seed_demo.py -i professor@uni.edu -s alice@uni.edu bob@uni.edu
    uv run python seed_demo.py -i professor@uni.edu -c algorithms

Available courses
-----------------
    software-arch  (default)  Introduction to Software Architecture
    algorithms                Data Structures and Algorithms
"""

import argparse
import sys

from dotenv import load_dotenv

from app.containers import Application
from app import models

load_dotenv()


# ---------------------------------------------------------------------------
# Hard-coded knowledge graphs
# ---------------------------------------------------------------------------


def _build_software_arch_course() -> models.RootKnowledge:
    """Introduction to Software Architecture."""

    # Build concepts first (IDs are assigned on construction) so that
    # connections can reference each concept's .id directly.

    # --- Layered Architecture -------------------------------------------

    proc_la_3 = models.ProceduralKnowledge(
        name="la_step_validate",
        label="Validate layer boundaries",
        difficulty=models.KnowledgeDifficulty.MEDIUM,
        bloom_level=models.KnowledgeProceduralBloomLevel.APPLY,
        common_errors=["Allowing calls that skip intermediate layers"],
        visibility=[models.KnowledgeVisibility.SUPERVISOR_AGENT],
        validation_status=models.KnowledgeValidationStatus.VERIFIED,
        confidence_score=0.95,
        relevance_score=0.90,
        source="Software Architecture: Patterns and Practices [p. 34]",
        learning_objective="Enforce strict layer boundaries to prevent tight coupling.",
        percent_done=0.0,
        child=None,
    )
    proc_la_2 = models.ProceduralKnowledge(
        name="la_step_assign",
        label="Assign responsibilities to each layer",
        difficulty=models.KnowledgeDifficulty.MEDIUM,
        bloom_level=models.KnowledgeProceduralBloomLevel.APPLY,
        common_errors=["Mixing business logic into the presentation layer"],
        visibility=[models.KnowledgeVisibility.SUPERVISOR_AGENT],
        validation_status=models.KnowledgeValidationStatus.VERIFIED,
        confidence_score=0.92,
        relevance_score=0.88,
        source="Software Architecture: Patterns and Practices [p. 28]",
        learning_objective="Clearly separate concerns across architecture layers.",
        percent_done=0.0,
        child=proc_la_3,
    )
    proc_la_1 = models.ProceduralKnowledge(
        name="la_step_identify",
        label="Identify the layers needed",
        difficulty=models.KnowledgeDifficulty.EASY,
        bloom_level=models.KnowledgeProceduralBloomLevel.APPLY,
        common_errors=[
            "Creating too many fine-grained layers",
            "Collapsing all logic into one layer",
        ],
        visibility=[models.KnowledgeVisibility.SUPERVISOR_AGENT],
        validation_status=models.KnowledgeValidationStatus.VERIFIED,
        confidence_score=0.97,
        relevance_score=0.92,
        source="Software Architecture: Patterns and Practices [p. 21]",
        learning_objective="Decompose a system into horizontal architectural layers.",
        percent_done=0.0,
        child=proc_la_2,
    )

    assess_la = models.AssessmentKnowledge(
        name="la_assessment",
        label="Layered Architecture Quiz",
        difficulty=models.KnowledgeDifficulty.MEDIUM,
        bloom_level=models.KnowledgeAssessmentBloomLevel.EVALUATE,
        linked_challenges=["quiz_layered_arch_01"],
        objectives=[
            "Identify the correct layer for a given responsibility",
            "Detect layer-boundary violations",
        ],
        question_prompts=[
            "Which layer should handle database queries?",
            "Is it acceptable for the presentation layer to call a gateway directly?",
        ],
        evaluation_criteria=[
            "Correct layer assignment",
            "Justification references separation of concerns",
        ],
    )

    # Concepts are built without connections first so their IDs exist.
    concept_la = models.ConceptualKnowledge(
        name="layered_architecture",
        label="Layered Architecture",
        difficulty=models.KnowledgeDifficulty.EASY,
        bloom_level=models.KnowledgeConceptualBloomLevel.UNDERSTAND,
        definition=(
            "A software architecture pattern that organises code into distinct horizontal layers "
            "(e.g. presentation, business logic, data access), each with a clearly defined responsibility."
        ),
        prerequisites=[],
        misconceptions=[
            "Layers can call each other in any direction",
            "Layered architecture and microservices are the same thing",
        ],
        visibility=[models.KnowledgeVisibility.SUPERVISOR_AGENT],
        validation_status=models.KnowledgeValidationStatus.VERIFIED,
        confidence_score=0.97,
        relevance_score=0.95,
        source="Software Architecture: Patterns and Practices [p. 18]",
        learning_objective="Understand the purpose and structure of layered architecture.",
        connections=[],  # wired after all concepts exist
        children=[proc_la_1, assess_la],
    )

    # --- Design Patterns ------------------------------------------------

    assess_dp = models.AssessmentKnowledge(
        name="dp_assessment",
        label="Design Patterns Evaluation",
        difficulty=models.KnowledgeDifficulty.HARD,
        bloom_level=models.KnowledgeAssessmentBloomLevel.CREATE,
        linked_challenges=["quiz_design_patterns_01"],
        objectives=[
            "Select the appropriate pattern for a given problem",
            "Justify the trade-offs of the chosen pattern",
        ],
        question_prompts=[
            "Which pattern provides a single point of access to a shared resource?",
            "How does the Strategy pattern differ from the Template Method pattern?",
        ],
        evaluation_criteria=[
            "Pattern correctly identified",
            "Trade-offs accurately described",
        ],
    )

    concept_dp = models.ConceptualKnowledge(
        name="design_patterns",
        label="Design Patterns",
        difficulty=models.KnowledgeDifficulty.MEDIUM,
        bloom_level=models.KnowledgeConceptualBloomLevel.UNDERSTAND,
        definition=(
            "Reusable, named solutions to commonly recurring design problems in object-oriented software, "
            "catalogued by the Gang of Four as Creational, Structural, and Behavioural patterns."
        ),
        prerequisites=["layered_architecture"],
        misconceptions=[
            "Patterns must always be applied",
            "More patterns equals better design",
        ],
        visibility=[models.KnowledgeVisibility.SUPERVISOR_AGENT],
        validation_status=models.KnowledgeValidationStatus.VERIFIED,
        confidence_score=0.93,
        relevance_score=0.91,
        source="Design Patterns: Elements of Reusable Object-Oriented Software [p. 1]",
        learning_objective="Recognise and apply classic design patterns to solve recurring design problems.",
        connections=[],  # wired after all concepts exist
        children=[assess_dp],
    )

    # --- Dependency Injection -------------------------------------------

    proc_di_2 = models.ProceduralKnowledge(
        name="di_step_wire",
        label="Wire providers in the DI container",
        difficulty=models.KnowledgeDifficulty.HARD,
        bloom_level=models.KnowledgeProceduralBloomLevel.ANALYZE,
        common_errors=[
            "Creating circular dependencies",
            "Registering the wrong scope (singleton vs transient)",
        ],
        visibility=[models.KnowledgeVisibility.SUPERVISOR_AGENT],
        validation_status=models.KnowledgeValidationStatus.VERIFIED,
        confidence_score=0.89,
        relevance_score=0.87,
        source="Dependency Injector Docs [containers]",
        learning_objective="Configure a DI container to resolve dependencies automatically.",
        percent_done=0.0,
        child=None,
    )
    proc_di_1 = models.ProceduralKnowledge(
        name="di_step_declare",
        label="Declare dependencies through the constructor",
        difficulty=models.KnowledgeDifficulty.MEDIUM,
        bloom_level=models.KnowledgeProceduralBloomLevel.APPLY,
        common_errors=[
            "Instantiating dependencies inside the class body",
            "Using global singletons instead of injected instances",
        ],
        visibility=[models.KnowledgeVisibility.SUPERVISOR_AGENT],
        validation_status=models.KnowledgeValidationStatus.VERIFIED,
        confidence_score=0.94,
        relevance_score=0.91,
        source="Dependency Injector Docs [providers]",
        learning_objective="Expose component dependencies through constructor parameters.",
        percent_done=0.0,
        child=proc_di_2,
    )

    concept_di = models.ConceptualKnowledge(
        name="dependency_injection",
        label="Dependency Injection",
        difficulty=models.KnowledgeDifficulty.MEDIUM,
        bloom_level=models.KnowledgeConceptualBloomLevel.UNDERSTAND,
        definition=(
            "A design technique where a component's dependencies are supplied by an external container "
            "rather than instantiated internally, promoting loose coupling and testability."
        ),
        prerequisites=["layered_architecture", "design_patterns"],
        misconceptions=[
            "Dependency injection requires a framework",
            "DI and the Service Locator pattern are the same",
        ],
        visibility=[models.KnowledgeVisibility.SUPERVISOR_AGENT],
        validation_status=models.KnowledgeValidationStatus.VERIFIED,
        confidence_score=0.92,
        relevance_score=0.90,
        source="Dependency Injector Docs [introduction]",
        learning_objective="Apply dependency injection to decouple components and facilitate testing.",
        connections=[],  # wired after all concepts exist
        children=[proc_di_1],
    )

    # --- Knowledge Graph Modelling --------------------------------------

    assess_kg = models.AssessmentKnowledge(
        name="kg_assessment",
        label="Knowledge Graph Modelling Assessment",
        difficulty=models.KnowledgeDifficulty.HARD,
        bloom_level=models.KnowledgeAssessmentBloomLevel.EVALUATE,
        linked_challenges=["quiz_kg_01"],
        objectives=[
            "Model a domain as a knowledge graph",
            "Select correct node types and relation types",
        ],
        question_prompts=[
            "What is the role of the RootKnowledge node?",
            "When would you use PREREQUISITE_FOR versus DEPENDS_ON?",
        ],
        evaluation_criteria=[
            "Graph is acyclic",
            "Relation types are semantically correct",
        ],
    )

    concept_kg = models.ConceptualKnowledge(
        name="knowledge_graph_modelling",
        label="Knowledge Graph Modelling",
        difficulty=models.KnowledgeDifficulty.HARD,
        bloom_level=models.KnowledgeConceptualBloomLevel.UNDERSTAND,
        definition=(
            "A method of representing domain knowledge as a directed graph of typed nodes "
            "(root, conceptual, procedural, assessment) and labelled edges, enabling structured "
            "retrieval and reasoning by AI agents."
        ),
        prerequisites=["dependency_injection"],
        misconceptions=[
            "A knowledge graph is just a database",
            "Any graph structure qualifies as a knowledge graph",
        ],
        visibility=[models.KnowledgeVisibility.SUPERVISOR_AGENT],
        validation_status=models.KnowledgeValidationStatus.VERIFIED,
        confidence_score=0.88,
        relevance_score=0.93,
        source="Course design docs [knowledge-graph.md]",
        learning_objective=(
            "Model a learning domain as a typed knowledge graph suitable for GraphRAG retrieval."
        ),
        connections=[],
        children=[assess_kg],
    )

    # Wire connections now that all concept IDs are known.
    concept_la.connections = [
        models.ConceptualKnowledgeConnection(
            relation=models.KnowledgeConceptualLinkType.ENABLES,
            to=concept_dp.id,
        ),
        models.ConceptualKnowledgeConnection(
            relation=models.KnowledgeConceptualLinkType.PREREQUISITE_FOR,
            to=concept_di.id,
        ),
    ]
    concept_dp.connections = [
        models.ConceptualKnowledgeConnection(
            relation=models.KnowledgeConceptualLinkType.EXTENDS_TO,
            to=concept_di.id,
        ),
    ]
    concept_di.connections = [
        models.ConceptualKnowledgeConnection(
            relation=models.KnowledgeConceptualLinkType.ENABLES,
            to=concept_kg.id,
        ),
    ]

    return models.RootKnowledge(
        name="Introduction to Software Architecture",
        description=(
            "A foundational course covering layered architecture, design patterns, "
            "dependency injection, and knowledge-graph modelling."
        ),
        sources=[
            "Software Architecture: Patterns and Practices",
            "Design Patterns: Elements of Reusable Object-Oriented Software",
            "Dependency Injector Docs",
        ],
        children=[concept_la, concept_dp, concept_di, concept_kg],
    )


def _build_algorithms_course() -> models.RootKnowledge:
    """Data Structures and Algorithms."""

    # --- Arrays and Linked Lists ----------------------------------------

    proc_ll_2 = models.ProceduralKnowledge(
        name="ll_step_traverse",
        label="Traverse the list and adjust pointers",
        difficulty=models.KnowledgeDifficulty.MEDIUM,
        bloom_level=models.KnowledgeProceduralBloomLevel.APPLY,
        common_errors=["Losing reference to next node before re-pointing", "Off-by-one on tail node"],
        visibility=[models.KnowledgeVisibility.SUPERVISOR_AGENT],
        validation_status=models.KnowledgeValidationStatus.VERIFIED,
        confidence_score=0.91,
        relevance_score=0.89,
        source="Introduction to Algorithms, 4th ed. [p. 258]",
        learning_objective="Implement insertion and deletion on a singly-linked list.",
        percent_done=0.0,
        child=None,
    )
    proc_ll_1 = models.ProceduralKnowledge(
        name="ll_step_node",
        label="Create a node with data and next pointer",
        difficulty=models.KnowledgeDifficulty.EASY,
        bloom_level=models.KnowledgeProceduralBloomLevel.APPLY,
        common_errors=["Forgetting to initialise next to None", "Mutating shared nodes"],
        visibility=[models.KnowledgeVisibility.SUPERVISOR_AGENT],
        validation_status=models.KnowledgeValidationStatus.VERIFIED,
        confidence_score=0.96,
        relevance_score=0.93,
        source="Introduction to Algorithms, 4th ed. [p. 250]",
        learning_objective="Represent a linked-list node as a data structure.",
        percent_done=0.0,
        child=proc_ll_2,
    )

    assess_arrays = models.AssessmentKnowledge(
        name="arrays_assessment",
        label="Arrays vs Linked Lists Quiz",
        difficulty=models.KnowledgeDifficulty.EASY,
        bloom_level=models.KnowledgeAssessmentBloomLevel.EVALUATE,
        linked_challenges=["quiz_arrays_01"],
        objectives=[
            "Compare time complexity of array and linked-list operations",
            "Choose the right structure for a given access pattern",
        ],
        question_prompts=[
            "What is the time complexity of inserting at the head of a linked list?",
            "Why does random access favour arrays over linked lists?",
        ],
        evaluation_criteria=[
            "Correct Big-O notation",
            "Access pattern justification is accurate",
        ],
    )

    concept_arrays = models.ConceptualKnowledge(
        name="arrays_and_linked_lists",
        label="Arrays and Linked Lists",
        difficulty=models.KnowledgeDifficulty.EASY,
        bloom_level=models.KnowledgeConceptualBloomLevel.REMEMBER,
        definition=(
            "Fundamental sequential data structures: arrays provide O(1) random access with fixed size; "
            "linked lists allow O(1) head insertion with dynamic size but O(n) random access."
        ),
        prerequisites=[],
        misconceptions=[
            "Linked lists are always faster than arrays",
            "Arrays and lists are interchangeable in all cases",
        ],
        visibility=[models.KnowledgeVisibility.SUPERVISOR_AGENT],
        validation_status=models.KnowledgeValidationStatus.VERIFIED,
        confidence_score=0.98,
        relevance_score=0.97,
        source="Introduction to Algorithms, 4th ed. [p. 247]",
        learning_objective="Distinguish between array and linked-list representations and their trade-offs.",
        connections=[],  # wired after all concepts exist
        children=[proc_ll_1, assess_arrays],
    )

    # --- Sorting Algorithms ---------------------------------------------

    proc_sort_2 = models.ProceduralKnowledge(
        name="sort_step_partition",
        label="Partition the array around a pivot",
        difficulty=models.KnowledgeDifficulty.HARD,
        bloom_level=models.KnowledgeProceduralBloomLevel.ANALYZE,
        common_errors=[
            "Choosing worst-case pivot (e.g. always first element on sorted input)",
            "Boundary errors during swap loop",
        ],
        visibility=[models.KnowledgeVisibility.SUPERVISOR_AGENT],
        validation_status=models.KnowledgeValidationStatus.VERIFIED,
        confidence_score=0.87,
        relevance_score=0.85,
        source="Introduction to Algorithms, 4th ed. [p. 183]",
        learning_objective="Implement the Lomuto or Hoare partition scheme correctly.",
        percent_done=0.0,
        child=None,
    )
    proc_sort_1 = models.ProceduralKnowledge(
        name="sort_step_choose",
        label="Choose a sorting algorithm for the problem constraints",
        difficulty=models.KnowledgeDifficulty.MEDIUM,
        bloom_level=models.KnowledgeProceduralBloomLevel.APPLY,
        common_errors=[
            "Using O(n²) sort on large inputs",
            "Ignoring stability requirements",
        ],
        visibility=[models.KnowledgeVisibility.SUPERVISOR_AGENT],
        validation_status=models.KnowledgeValidationStatus.VERIFIED,
        confidence_score=0.93,
        relevance_score=0.91,
        source="Introduction to Algorithms, 4th ed. [p. 170]",
        learning_objective="Select the appropriate sorting algorithm based on input size and constraints.",
        percent_done=0.0,
        child=proc_sort_2,
    )

    assess_sort = models.AssessmentKnowledge(
        name="sort_assessment",
        label="Sorting Algorithms Assessment",
        difficulty=models.KnowledgeDifficulty.MEDIUM,
        bloom_level=models.KnowledgeAssessmentBloomLevel.EVALUATE,
        linked_challenges=["quiz_sorting_01", "quiz_sorting_02"],
        objectives=[
            "State the time and space complexity of major sorting algorithms",
            "Implement quicksort partition correctly",
        ],
        question_prompts=[
            "What is the average-case complexity of quicksort?",
            "When is merge sort preferred over quicksort?",
        ],
        evaluation_criteria=[
            "Big-O bounds are correct",
            "Stability and space trade-offs are addressed",
        ],
    )

    concept_sort = models.ConceptualKnowledge(
        name="sorting_algorithms",
        label="Sorting Algorithms",
        difficulty=models.KnowledgeDifficulty.MEDIUM,
        bloom_level=models.KnowledgeConceptualBloomLevel.UNDERSTAND,
        definition=(
            "Algorithms that reorder a collection of elements into a defined sequence. "
            "Key examples include bubble sort O(n²), merge sort O(n log n), and quicksort O(n log n) average."
        ),
        prerequisites=["arrays_and_linked_lists"],
        misconceptions=[
            "Quicksort is always faster than merge sort",
            "A stable sort is always required",
        ],
        visibility=[models.KnowledgeVisibility.SUPERVISOR_AGENT],
        validation_status=models.KnowledgeValidationStatus.VERIFIED,
        confidence_score=0.94,
        relevance_score=0.92,
        source="Introduction to Algorithms, 4th ed. [p. 168]",
        learning_objective="Analyse and implement comparison-based sorting algorithms.",
        connections=[],  # wired after all concepts exist
        children=[proc_sort_1, assess_sort],
    )

    # --- Hash Tables ----------------------------------------------------

    assess_ht = models.AssessmentKnowledge(
        name="ht_assessment",
        label="Hash Tables Assessment",
        difficulty=models.KnowledgeDifficulty.MEDIUM,
        bloom_level=models.KnowledgeAssessmentBloomLevel.CREATE,
        linked_challenges=["quiz_hash_tables_01"],
        objectives=[
            "Explain how a hash function distributes keys",
            "Describe collision resolution strategies",
        ],
        question_prompts=[
            "What happens when two keys hash to the same index?",
            "Why is load factor important for hash table performance?",
        ],
        evaluation_criteria=[
            "Collision strategy correctly described",
            "Load factor impact on complexity is accurate",
        ],
    )

    concept_ht = models.ConceptualKnowledge(
        name="hash_tables",
        label="Hash Tables",
        difficulty=models.KnowledgeDifficulty.MEDIUM,
        bloom_level=models.KnowledgeConceptualBloomLevel.UNDERSTAND,
        definition=(
            "A data structure that maps keys to values via a hash function, providing O(1) average-case "
            "lookup, insertion, and deletion. Collisions are handled by chaining or open addressing."
        ),
        prerequisites=["arrays_and_linked_lists"],
        misconceptions=[
            "Hash tables guarantee O(1) worst-case",
            "Any hash function is equally good",
        ],
        visibility=[models.KnowledgeVisibility.SUPERVISOR_AGENT],
        validation_status=models.KnowledgeValidationStatus.VERIFIED,
        confidence_score=0.90,
        relevance_score=0.88,
        source="Introduction to Algorithms, 4th ed. [p. 272]",
        learning_objective="Use hash tables to implement efficient key-value lookups.",
        connections=[],  # wired after all concepts exist
        children=[assess_ht],
    )

    # Wire connections now that all concept IDs are known.
    concept_arrays.connections = [
        models.ConceptualKnowledgeConnection(
            relation=models.KnowledgeConceptualLinkType.PREREQUISITE_FOR,
            to=concept_sort.id,
        ),
        models.ConceptualKnowledgeConnection(
            relation=models.KnowledgeConceptualLinkType.ENABLES,
            to=concept_ht.id,
        ),
    ]
    concept_sort.connections = [
        models.ConceptualKnowledgeConnection(
            relation=models.KnowledgeConceptualLinkType.DEPENDS_ON,
            to=concept_arrays.id,
        ),
    ]
    concept_ht.connections = [
        models.ConceptualKnowledgeConnection(
            relation=models.KnowledgeConceptualLinkType.DEPENDS_ON,
            to=concept_arrays.id,
        ),
    ]

    return models.RootKnowledge(
        name="Data Structures and Algorithms",
        description=(
            "A practical course covering fundamental data structures (arrays, linked lists, hash tables) "
            "and algorithms (sorting, searching) with complexity analysis."
        ),
        sources=["Introduction to Algorithms, 4th ed. (CLRS)"],
        children=[concept_arrays, concept_sort, concept_ht],
    )


# ---------------------------------------------------------------------------
# Course registry
# ---------------------------------------------------------------------------

_COURSES: dict[str, tuple[str, callable]] = {
    "software-arch": (
        "Introduction to Software Architecture",
        _build_software_arch_course,
    ),
    "algorithms": (
        "Data Structures and Algorithms",
        _build_algorithms_course,
    ),
}

_DEFAULT_COURSE = "software-arch"


# ---------------------------------------------------------------------------
# Hard-coded demo trajectories
# ---------------------------------------------------------------------------

_DEMO_TRAJECTORIES = [
    # Normal interactions (no hint)
    {
        "query": "What is the difference between a service and a repository?",
        "interaction_type": "concept_request",
        "hint_triggered": False,
    },
    {
        "query": "Can you explain how dependency injection works in this project?",
        "interaction_type": "concept_request",
        "hint_triggered": False,
    },
    {
        "query": "How do I run the tests?",
        "interaction_type": "code_request",
        "hint_triggered": False,
    },
    # Pending hints (awaiting instructor review)
    {
        "query": "How does the knowledge graph relate to Bloom's taxonomy?",
        "interaction_type": "concept_request",
        "hint_triggered": True,
        "hint_reason": "Repeated query — possible conceptual confusion",
        "hint_text": (
            "Think about how Bloom's taxonomy organises learning objectives from simple recall up to "
            "evaluation. Which node type in the graph maps to each level?"
        ),
        "hint_approval_status": models.HintApprovalStatus.PENDING,
    },
    {
        "query": "Why do procedural nodes form a linked list?",
        "interaction_type": "concept_request",
        "hint_triggered": True,
        "hint_reason": "Procedural impasse — stuck on how-to steps",
        "hint_text": (
            "A linked list enforces a strict ordering of steps. Ask yourself: does the order of "
            "these steps matter, and what happens if you skip one?"
        ),
        "hint_approval_status": models.HintApprovalStatus.PENDING,
    },
    # Approved hints (already visible to the student)
    {
        "query": "I keep getting confused about ConceptualKnowledge connections.",
        "interaction_type": "concept_request",
        "hint_triggered": True,
        "hint_reason": "Repeated query — possible conceptual confusion",
        "hint_text": (
            "Each connection has a relation type (e.g. PREREQUISITE_FOR, EXTENDS_TO). "
            "Try drawing two concept nodes on paper and labelling the arrow — "
            "which direction does knowledge flow?"
        ),
        "hint_approval_status": models.HintApprovalStatus.APPROVED,
    },
    {
        "query": "What is the role of the RootKnowledge node?",
        "interaction_type": "concept_request",
        "hint_triggered": True,
        "hint_reason": "Repeated query — possible conceptual confusion",
        "hint_text": (
            "The root is the entry point of the entire graph — like the cover of a textbook. "
            "Everything else hangs off it. Focus on what makes it different from a ConceptualKnowledge node."
        ),
        "hint_approval_status": models.HintApprovalStatus.APPROVED,
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_user(user_service, email: str) -> models.User:
    user = user_service.get_user_by_email(email)
    if not user:
        print(f"[error] No user found with email '{email}'. Register them first.")
        sys.exit(1)
    return user


def _seed_student(user_service, student: models.User, course_id: str) -> None:
    print(f"  → seeding trajectories for {student.email} …")
    for data in _DEMO_TRAJECTORIES:
        trajectory = models.UserTrajectory(
            user_id=student.id,
            course_id=course_id,
            query=data["query"],
            interaction_type=data["interaction_type"],
            retrieved_nodes=["Demo Node A", "Demo Node B"],
            scores=[0.91, 0.84],
            query_repeat_count=1 if data["hint_triggered"] else 0,
            node_entry_count=2,
            response_time_sec=0.0,
            hint_triggered=data["hint_triggered"],
            hint_reason=data.get("hint_reason"),
            hint_text=data.get("hint_text"),
            hint_approval_status=data.get("hint_approval_status"),
        )
        user_service.add_trajectory_entry(student.id, trajectory)

    approved = sum(
        1
        for d in _DEMO_TRAJECTORIES
        if d.get("hint_approval_status") == models.HintApprovalStatus.APPROVED
    )
    pending = sum(
        1
        for d in _DEMO_TRAJECTORIES
        if d.get("hint_approval_status") == models.HintApprovalStatus.PENDING
    )
    print(
        f"     {len(_DEMO_TRAJECTORIES)} trajectories created "
        f"({approved} approved hints, {pending} pending hints)"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed a demo course with a hard-coded knowledge graph and sample hints."
    )
    parser.add_argument(
        "-i", "--instructor",
        required=True,
        metavar="EMAIL",
        help="Email of an existing instructor user.",
    )
    parser.add_argument(
        "-s", "--students",
        nargs="+",
        required=True,
        metavar="EMAIL",
        help="Emails of existing student users (at least one required).",
    )
    parser.add_argument(
        "-c", "--course",
        choices=list(_COURSES.keys()),
        default=_DEFAULT_COURSE,
        metavar="COURSE",
        help=(
            f"Which demo course to seed (default: {_DEFAULT_COURSE!r}). "
            f"Available: {', '.join(_COURSES.keys())}."
        ),
    )
    args = parser.parse_args()

    course_label, course_builder = _COURSES[args.course]

    # Bootstrap the DI container (no Flask needed).
    container = Application()
    container.init_resources()

    user_service = container.services.user()
    knowledge_service = container.services.knowledge()

    # Resolve users.
    instructor = _require_user(user_service, args.instructor)
    students = [_require_user(user_service, email) for email in args.students]

    print(f"\nInstructor : {instructor.name} <{instructor.email}>")
    print(f"Students   : {', '.join(s.email for s in students)}")

    # Build and persist the hard-coded knowledge graph.
    print(f"\nBuilding knowledge graph for '{course_label}' …")
    root_knowledge = course_builder()

    course_id = knowledge_service.create_knowledge(root_knowledge)
    print(f"  course id : {course_id}")
    print(f"  concepts  : {len(root_knowledge.children)}")

    # Assign members.
    knowledge_service.set_course_instructors(course_id, [instructor.id])
    knowledge_service.set_course_students(course_id, [s.id for s in students])

    # Seed trajectories.
    print("Seeding student trajectories …")
    for student in students:
        _seed_student(user_service, student, course_id)

    print(f"\nDone. Course '{course_label}' is ready (id={course_id}).\n")


if __name__ == "__main__":
    main()
