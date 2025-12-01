def build_candidate_details(profile: dict) -> str:
    """
    Converts UI profile dict into the exact format
    expected by the LLM prompt.
    """

    lines = []

    if profile.get("position"):
        lines.append(f"Position: {profile['position']}")

    if profile.get("skills"):
        lines.append(f"Skills: {profile['skills']}")

    if profile.get("summary"):
        lines.append("More info:")
        lines.append(profile["summary"])

    if profile.get("looking_for"):
        lines.append("Looking For:")
        lines.append(profile["looking_for"])

    if profile.get("highlights"):
        lines.append("Highlights:")
        lines.append(profile["highlights"])

    if profile.get("primary_keyword"):
        lines.append(f"Primary Keyword: {profile['primary_keyword']}")

    return "\n".join(lines)
