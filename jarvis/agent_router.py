"""
Agent Router — maps incoming requests to the right Marvel agent domain.

Routing is based on keyword signals in the request text, active context
(time of day, family mode), and explicit domain hints.

This does NOT call LLMs for routing — it uses fast heuristic matching
to stay below 20ms. The matched agent_id is then used to:
1. Select the right persona snippet for the system prompt
2. Tag the work item with the responsible agent
3. Surface "already working" credits in the UI
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class RouteResult:
    agent_id: str
    agent_label: str
    domain: str
    confidence: float  # 0.0–1.0
    signals: list[str] = field(default_factory=list)  # which keywords triggered this route


# Domain keyword maps: agent_id → (label, domain, keywords)
DOMAIN_ROUTES: list[tuple[str, str, str, list[str]]] = [
    ("nick-fury",         "Nick Fury",         "strategy",       ["brief", "briefing", "status", "priority", "mission", "strategic", "intel", "intelligence", "what matters", "what's happening"]),
    ("kang",              "Kang",               "calendar",       ["calendar", "schedule", "appointment", "meeting", "event", "time", "when", "deadline", "tomorrow", "today", "week"]),
    ("natasha",           "Natasha",            "inbox",          ["email", "message", "inbox", "slack", "text", "respond", "reply", "communicate", "communication", "triage"]),
    ("pepper",            "Pepper",             "household",      ["household", "family status", "home status", "chief of staff", "what's handled", "what's organized"]),
    ("wanda",             "Wanda",              "domestic",       ["kids", "caleb", "anna", "rebekah", "dinner", "groceries", "family", "routine", "school", "pickup", "drop"]),
    ("maria-hill",        "Maria Hill",         "travel",         ["travel", "trip", "flight", "hotel", "vacation", "visit", "drive", "route", "directions"]),
    ("storm",             "Storm",              "weather",        ["weather", "rain", "temperature", "forecast", "storm", "wind", "sunny", "cold", "hot", "outside"]),
    ("fisk",              "Fisk",               "finance",        ["money", "finance", "budget", "invest", "income", "expense", "bank", "stock", "portfolio", "wealth", "capital", "cash"]),
    ("workshop-foreman",  "Tony",               "workshop",       ["print", "3d", "laser", "cnc", "workshop", "make", "build", "fabricate", "design", "model", "prototype", "forge", "cricut"]),
    ("ultron",            "Ultron",             "security",       ["security", "door", "garage", "lock", "camera", "alert", "sensor", "smoke", "alarm", "safe", "threat"]),
    ("thor",              "Thor",               "health",         ["health", "fitness", "exercise", "workout", "run", "walk", "sleep", "hydration", "water", "weight", "body"]),
    ("formation-director","One Above All",      "faith",          ["faith", "pray", "prayer", "scripture", "bible", "verse", "devotion", "spiritual", "god", "church", "formation", "worship"]),
    ("chronicle-curator", "Disciple",           "chronicle",      ["chronicle", "journal", "reflection", "record", "remember", "memory entry", "log entry", "daily log", "capture the moment"]),
    ("catalyst-personal", "Mantis",             "workflow",       ["catalyst", "workflow", "project", "task", "work", "focus", "block", "next action", "planning", "overwhelm"]),
    ("executive-counsel", "T'Challa",           "strategy",       ["strategy", "decision", "advise", "counsel", "think through", "options", "tradeoff", "long term", "plan"]),
    ("loki",              "Loki",               "marketing",      ["marketing", "promote", "audience", "content", "brand", "social", "post", "campaign", "launch"]),
    ("gamora",            "Gamora",             "relationships",  ["friend", "relationship", "reach out", "connect", "birthday", "anniversary", "gift", "thank", "appreciate"]),
    ("professor-x",       "Professor X",        "tutoring",       ["tutor", "homework", "study", "learn", "caleb school", "anna school", "help with", "explain", "teach"]),
    ("spider-man",        "Spider-Man",         "signals",        ["news", "signal", "world", "industry", "trend", "watch", "noticed", "alert me", "keep an eye"]),
    ("workshop-foreman",  "Tony",               "workshop",       ["printer", "halot", "falcon laser", "titoe", "k2 pro", "filament", "resin"]),
    ("stan-lee",          "Stan Lee",           "writing",        ["write", "writing", "manuscript", "chapter", "draft", "ghostwritr", "book", "author", "edit"]),
    ("robbie-robertson",  "Robbie Robertson",   "publishing",     ["publish", "amazon", "kindle", "distribute", "royalty", "isbn", "kdp"]),
    ("jjj",               "J. Jonah Jameson",   "social",         ["twitter", "instagram", "linkedin", "social media", "post", "tweet", "platform", "follower"]),
    ("iron-fist",         "Iron Fist",          "courses",        ["course", "training", "coursera", "udemy", "module", "curriculum", "teach online"]),
    ("amadeus-cho",       "Amadeus Cho",        "web",            ["website", "web", "domain", "hosting", "analytics", "site", "page", "seo"]),
    ("troop-pathfinder",  "Patriot",            "scouting",       ["scout", "troop", "merit badge", "camping", "eagle", "boy scout", "cub scout"]),
    ("helen-cho",         "Helen Cho",          "medical",        ["doctor", "medical", "health record", "appointment", "prescription", "sick", "hurt", "injury", "medication"]),
    ("howard-stark",      "Howard Stark",       "passive_income", ["passive income", "royalty", "revenue stream", "book sales", "course revenue", "income stream"]),
    ("reed-richards",     "Reed Richards",      "maintenance",    ["repair", "fix", "maintenance", "plumbing", "electrical", "hvac", "roof", "contractor", "home repair"]),
    ("mockingbird",       "Mockingbird",        "rebekah",        ["rebekah", "wife", "she needs", "she wants", "rebekah's", "for rebekah"]),
    ("nova",              "Nova",               "growth",         ["grow", "learn", "skill", "read", "book recommendation", "podcast", "improve myself", "personal development"]),
    ("agatha",            "Agatha",             "occasions",      ["gift", "occasion", "birthday", "anniversary", "holiday", "celebrate", "surprise", "special"]),
    ("vision",            "Vision",             "systems",        ["system", "integration", "api", "connect", "sync", "home assistant", "automation", "device"]),
    ("beast",             "Beast",              "research",       ["research", "look up", "search results", "find facts", "information on", "background on", "data on", "facts about", "explain how", "what does"]),
]


def route_request(text: str, context: dict | None = None) -> RouteResult:
    """
    Route a request to the most appropriate agent domain.
    Returns the best match or defaults to nick-fury (briefing/general).
    """
    text_lower = text.lower()
    context = context or {}

    scores: list[tuple[float, tuple]] = []

    for agent_id, label, domain, keywords in DOMAIN_ROUTES:
        matched = [kw for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', text_lower)]
        if matched:
            # Score = absolute match count (primary) + match density (secondary)
            # This ensures an agent with more keyword hits beats one with
            # a better hit rate but fewer actual matches.
            score = len(matched) + (len(matched) / len(keywords))
            scores.append((score, (agent_id, label, domain, matched)))

    if not scores:
        # Default to Nick Fury for general briefing/unknown
        return RouteResult(
            agent_id="nick-fury",
            agent_label="Nick Fury",
            domain="general",
            confidence=0.1,
            signals=["default"],
        )

    scores.sort(reverse=True, key=lambda x: x[0])
    best_score, (agent_id, label, domain, signals) = scores[0]

    return RouteResult(
        agent_id=agent_id,
        agent_label=label,
        domain=domain,
        confidence=min(best_score, 1.0),
        signals=signals,
    )


def route_by_domain(domain: str) -> RouteResult:
    """Get the primary agent for a given domain name."""
    for agent_id, label, agent_domain, _keywords in DOMAIN_ROUTES:
        if agent_domain == domain:
            return RouteResult(
                agent_id=agent_id,
                agent_label=label,
                domain=domain,
                confidence=1.0,
                signals=[],
            )
    return RouteResult(
        agent_id="nick-fury",
        agent_label="Nick Fury",
        domain="general",
        confidence=0.5,
        signals=[],
    )


def get_agents_for_event(event_type: str) -> list[RouteResult]:
    """
    Return list of agents that should be notified/triggered for a given event type.
    Maps event types to responsible agents.
    """
    event_agent_map: dict[str, list[str]] = {
        "morning":          ["nick-fury", "pepper", "storm", "kang", "thor"],
        "evening":          ["pepper", "wanda", "nick-fury"],
        "home_arrival":     ["pepper", "ultron", "wanda"],
        "home_departure":   ["ultron", "falcon"],
        "calendar_update":  ["kang", "natasha", "pepper"],
        "message_received": ["natasha"],
        "security_alert":   ["ultron", "watchtower"],
        "weather_alert":    ["storm", "pepper"],
        "approval_needed":  ["nick-fury"],
    }

    agent_ids = event_agent_map.get(event_type, ["nick-fury"])
    results: list[RouteResult] = []

    # Build a quick lookup from DOMAIN_ROUTES (first occurrence per agent_id wins)
    agent_lookup: dict[str, tuple[str, str]] = {}
    for a_id, label, domain, _keywords in DOMAIN_ROUTES:
        if a_id not in agent_lookup:
            agent_lookup[a_id] = (label, domain)

    for agent_id in agent_ids:
        if agent_id in agent_lookup:
            label, domain = agent_lookup[agent_id]
            results.append(
                RouteResult(
                    agent_id=agent_id,
                    agent_label=label,
                    domain=domain,
                    confidence=1.0,
                    signals=[event_type],
                )
            )
        else:
            # Agent referenced in event map but not in DOMAIN_ROUTES — include with defaults
            results.append(
                RouteResult(
                    agent_id=agent_id,
                    agent_label=agent_id,
                    domain="general",
                    confidence=1.0,
                    signals=[event_type],
                )
            )

    return results
