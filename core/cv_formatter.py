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

    education = profile.get("education", {})
    if any(education.values()):
        lines.append("Education:")
        if education.get("degree"):
            lines.append(f"- Degree: {education['degree']}")
        if education.get("university"):
            lines.append(f"- University: {education['university']}")
        if education.get("year"):
            lines.append(f"- Graduation Year: {education['year']}")

    experience = profile.get("profile_experience", {})
    if any(experience.values()):
        lines.append("Experience:")
        if experience.get("company"):
            lines.append(f"- Company: {experience['company']}")
        if experience.get("position"):
            lines.append(f"- Position: {experience['position']}")
        if experience.get("type"):
            lines.append(f"- Employment type: {experience['type']}")
        if experience.get("years"):
            lines.append(f"- Working Years: {experience['years']}")

    return "\n".join(lines)