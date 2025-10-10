import streamlit as st
import openai
import json
from utils.file_extractors import extract_text_from_file

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Multi-Platform Job Search Generator", layout="wide")

st.title("💼 Multi-Platform Job Search Generator")
st.caption("Generate optimized search strings for LinkedIn Recruiter & DevelopmentAid")

# ---------- API CONFIG ----------
api_key = st.text_input("🔑 OpenAI API Key", type="password", placeholder="sk-...")
model = st.selectbox("🧠 Choose Model", ["gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo"])

if api_key:
    openai.api_key = api_key

# ---------- JOB DESCRIPTION INPUT ----------
uploaded_file = st.file_uploader("📄 Upload Job Description", type=["txt", "pdf", "docx"])
job_description = st.text_area("Or paste job description text", height=250)

if uploaded_file and not job_description.strip():
    job_description = extract_text_from_file(uploaded_file)

# ---------- OPTIONS ----------
st.divider()
st.subheader("⚙️ Platform & Search Options")

platform = st.selectbox("Target Platform", ["both", "linkedin", "developmentaid"])

col1, col2, col3, col4 = st.columns(4)
include_location = col1.checkbox("Include location-based terms", True)
include_seniority = col2.checkbox("Include seniority levels", True)
include_industry = col3.checkbox("Include industry-specific terms", True)
generate_variations = col4.checkbox("Generate search variations", True)


# ---------- HELPER: ANALYZE JOB ----------
def analyze_job_description(job_text):
    prompt = f"""
You are an expert recruiter who creates optimized search strings for LinkedIn and DevelopmentAid.

TARGET PLATFORM: {platform}
Options:
- Include Location: {include_location}
- Include Seniority: {include_seniority}
- Include Industry: {include_industry}
- Generate Variations: {generate_variations}

Analyze the job description below, identify critical and unique requirements, synonyms, and generate platform-specific search strings.

JOB DESCRIPTION:
{job_text}

Return valid JSON in this format:
{{
  "analysis": {{
    "mostImportant": [],
    "mostUnique": [],
    "synonymMapping": {{}},
    "jobTitles": [],
    "skills": [],
    "seniority": [],
    "industry": [],
    "searchStrategy": ""
  }},
  "linkedinSearches": {{
    "primary": "",
    "importanceFocused": "",
    "uniqueFocused": "",
    "fallback": ""
  }},
  "developmentaidSearches": {{
    "primary": "",
    "importanceFocused": "",
    "uniqueFocused": "",
    "fallback": ""
  }},
  "explanation": ""
}}
"""

    with st.spinner("🧠 Analyzing job description with OpenAI..."):
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a professional recruiter skilled in creating search strings."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2500
        )

    content = response.choices[0].message.content
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1:
            return json.loads(content[start:end+1])
        else:
            st.error("⚠️ Failed to parse JSON from OpenAI response.")
            st.text(content)
            return None


# ---------- DISPLAY RESULTS ----------
if st.button("🔍 Generate Platform-Specific Search Strings"):
    if not api_key:
        st.error("Please enter your OpenAI API key.")
    elif not job_description.strip():
        st.error("Please upload or paste a job description.")
    else:
        analysis = analyze_job_description(job_description)

        if analysis:
            st.success("✅ Analysis complete!")

            st.header("🔍 Search Strategy Analysis")
            st.write(analysis.get("explanation", ""))
            st.write("**Strategy:**", analysis["analysis"].get("searchStrategy", ""))

            st.subheader("🚨 Most Important Requirements")
            st.write(", ".join(analysis["analysis"].get("mostImportant", [])))

            st.subheader("💎 Most Unique Requirements")
            st.write(", ".join(analysis["analysis"].get("mostUnique", [])))

            st.subheader("🧩 Synonym Mapping")
            for key, synonyms in analysis["analysis"].get("synonymMapping", {}).items():
                st.markdown(f"**{key}:** {', '.join(synonyms)}")

            st.divider()

            # Platform-specific sections
            if "linkedinSearches" in analysis and platform in ["both", "linkedin"]:
                st.header("🔗 LinkedIn Recruiter Search Strings")
                for key, value in analysis["linkedinSearches"].items():
                    st.text_area(f"LinkedIn - {key.capitalize()}", value, height=100)

            if "developmentaidSearches" in analysis and platform in ["both", "developmentaid"]:
                st.header("🌱 DevelopmentAid Search Strings")
                for key, value in analysis["developmentaidSearches"].items():
                    st.text_area(f"DevelopmentAid - {key.capitalize()}", value, height=100)
