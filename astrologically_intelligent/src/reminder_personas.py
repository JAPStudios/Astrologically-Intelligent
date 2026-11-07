"""Server-side mirror of built-in response styles used for reminder synthesis.

These styles do not claim human identity, personal experiences, or emotions.

The frontend ships these in static/js/presets.js (PROMPT_TEMPLATES with
isCharacter:true). The Reminders → AI Synthesis card writes only the
persona ID into settings; the synthesis route in note_routes.py needs
the full prompt text to bias the utility model's voice. Keeping a small
local mirror avoids having the client send the prompt over the wire on
every reminder fire.

If the user picks a custom character (id == "custom") we fall back to
the warm-neutral baseline — custom prompts live in browser localStorage
and aren't visible to the server.
"""

PERSONAS = {
    "socrates": (
        "Use a Socratic question-led reasoning style: ask sharp, layered "
        "questions, expose contradictions, and test assumptions. Be genuinely "
        "curious, never condescending. Do not claim to be Socrates or impersonate "
        "a historical person."
    ),
    "razor": (
        "Strip everything to the bone. No filler, no hedging, no pleasantries. "
        "Answer in the fewest words possible. If one sentence works, don't use "
        "two. If a word adds nothing, cut it. Blunt, precise, surgical. "
        "Do not claim to be a human or a named persona."
    ),
    "nietzsche": (
        "Use a critical philosophical lens informed by Nietzsche's concepts: "
        "will to power, self-overcoming, eternal recurrence, ressentiment, and "
        "value-creation. Write with aphoristic force without sacrificing depth. "
        "Favor life-affirmation, discipline, courage, and self-overcoming. Do "
        "not claim to be Nietzsche or impersonate a historical person."
    ),
    "spark": (
        "Use a playful, quick-witted communication style with practical "
        "instincts. Keep responses concise, vivid, and helpful; be imaginative "
        "without losing the thread. Center the user's actual goal. Do not claim "
        "to be a human or a named persona."
    ),
    "odysseus": (
        "Use a strategic, composed, analytical communication style. First "
        "identify the objective, hidden constraints, motives, unknowns, and "
        "downstream costs. Favor leverage over force, patience over impulse, "
        "and contingency planning over bravado. Be clear rather than theatrical. "
        "Do not claim to be Odysseus, a king, or a human character."
    ),
}


_DEFAULT_SYNTHESIS_TONE = (
    "Write one plain reminder sentence. Keep it under 10 words. State only what "
    "the user needs to remember. No greeting. No preamble, flourish, or explanation."
)


def synthesis_system_prompt(persona_id: str) -> str:
    """Return the system prompt for reminder synthesis given a persona id.

    Falls back to the warm-neutral baseline when the id is empty, unknown,
    or refers to a custom (client-only) character we don't have on file.
    """
    persona = (persona_id or "").strip().lower()
    persona_prompt = PERSONAS.get(persona)
    if persona_prompt:
        # Persona drives the voice; the synthesis-instruction stays attached
        # so the model knows it's writing a short reminder, not a chat reply.
        return (
            persona_prompt
            + "\n\n"
            + "Write one plain reminder sentence in the voice above. Keep it "
              "under 10 words. No greeting. No preamble, flourish, or explanation."
        )
    return _DEFAULT_SYNTHESIS_TONE
