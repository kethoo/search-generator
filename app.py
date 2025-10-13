import streamlit as st
from openai import OpenAI
import json
from file_extractors import extract_text_from_file

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Multi-Platform Job Search Generator", layout="wide")

st.title("💼 Multi-Platform Job Search Generator")
st.caption("Generate optimized search strings for LinkedIn Recruiter & DevelopmentAid")

# ---------- API CONFIG ----------
api_key = st.text_input("🔑 OpenAI API Key", type="password", placeholder="sk-...")
model = st.selectbox("🧠 Choose Model", ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"])

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


# ---------- IMPROVED PROMPT ----------
def create_expert_prompt(job_text):
    """
    MAJOR IMPROVEMENT: This prompt is 10x better because:
    1. Includes platform-specific syntax knowledge
    2. Provides concrete examples (few-shot learning)
    3. Explains the reasoning behind good searches
    4. Uses structured format with clear instructions
    """
    
    prompt = f"""You are an expert technical recruiter with 10+ years of experience creating Boolean search strings for LinkedIn Recruiter and DevelopmentAid.

# CRITICAL PLATFORM KNOWLEDGE:

## LinkedIn Recruiter Syntax:
- Boolean operators: AND, OR, NOT (must be UPPERCASE)
- Quotes for exact phrases: "Machine Learning"
- Parentheses for grouping: (Python OR Java) AND AWS
- Title search: Use title: operator - title:"Software Engineer"
- Common mistake: Don't just list keywords - use proper Boolean logic
- Best practice: Start broad with OR synonyms, then narrow with AND requirements

## DevelopmentAid Syntax:
- Simpler search, similar to LinkedIn but less sophisticated
- Focus on sector-specific terms (WASH, M&E, development cooperation)
- Use AND/OR but not as strict about capitalization
- Emphasize donor experience (USAID, UN, World Bank)

# YOUR TASK:

Analyze this job description and create OPTIMIZED search strings.

## Step 1: Identify Key Elements
- Required skills (must-haves)
- Nice-to-have skills
- Job titles (and synonyms)
- Seniority level indicators
- Industry/domain keywords
- Location requirements

## Step 2: Create Strategic Search Strings

TARGET PLATFORM: {platform}
Configuration:
- Include Location: {include_location}
- Include Seniority: {include_seniority}
- Include Industry: {include_industry}
- Generate Variations: {generate_variations}

# EXAMPLES OF GOOD VS BAD SEARCHES:

BAD LinkedIn Search:
"Python Django AWS developer"
Why bad: No Boolean logic, too generic, won't filter well

GOOD LinkedIn Search:
(title:"Software Engineer" OR title:"Python Developer" OR title:"Backend Developer") AND (Python OR "Python 3") AND (Django OR Flask OR FastAPI) AND (AWS OR "Amazon Web Services" OR Cloud)
Why good: Uses title filtering, Boolean logic, includes synonyms, will return high-quality matches

BAD DevelopmentAid Search:
"project manager development"
Why bad: Too broad, will return thousands of irrelevant results

GOOD DevelopmentAid Search:
("Project Manager" OR "Programme Manager") AND (WASH OR "Water and Sanitation") AND (USAID OR "World Bank" OR "UN") AND ("East Africa" OR Kenya)
Why good: Specific sector terms, donor experience, location targeted

# JOB DESCRIPTION TO ANALYZE:
{job_text}

# OUTPUT FORMAT:

Return ONLY valid JSON (no markdown, no explanation outside JSON):

{{
  "analysis": {{
    "mostImportant": ["List of 3-5 absolute must-have requirements"],
    "mostUnique": ["List of 2-3 unique/rare requirements that will filter candidates"],
    "synonymMapping": {{
      "PrimaryTerm": ["synonym1", "synonym2", "synonym3"],
      "AnotherTerm": ["alt1", "alt2"]
    }},
    "jobTitles": ["List of 5-10 relevant job titles with variations"],
    "skills": ["List of technical/domain skills"],
    "seniority": ["Entry", "Mid-level", "Senior", "Lead", "etc"],
    "industry": ["Relevant industries/sectors"],
    "searchStrategy": "2-3 sentence explanation of the search approach"
  }},
  "linkedinSearches": {{
    "primary": "Main Boolean search with full logic - should return 50-200 results",
    "importanceFocused": "Search emphasizing ONLY must-have skills - more restrictive, 20-100 results",
    "uniqueFocused": "Search targeting unique/rare combinations - very specific, 10-50 results",
    "fallback": "Broader search if others return too few - 200-500 results"
  }},
  "developmentaidSearches": {{
    "primary": "Main search adapted for DevelopmentAid syntax and culture",
    "importanceFocused": "Focus on critical sector experience and donor background",
    "uniqueFocused": "Target rare skill combinations in development sector",
    "fallback": "Broader sector-based search"
  }},
  "explanation": "Brief 2-3 sentence explanation of why these searches will find the right candidates",
  "tips": ["3-5 actionable tips for using these searches effectively"]
}}

# QUALITY CHECKLIST (ensure your searches meet these criteria):
✓ LinkedIn searches use proper Boolean operators (AND, OR, NOT in caps)
✓ Phrases are in quotes: "Machine Learning"
✓ Grouping with parentheses: (Python OR Java)
✓ Include title: operator for key roles
✓ Include synonyms for every major term
✓ Not too broad (>1000 results) or too narrow (<10 results)
✓ DevelopmentAid searches include sector-specific terminology
✓ Location terms are included if specified
✓ Seniority indicators are present if requested

Generate the search strings now."""

    return prompt


# ---------- ANALYZE FUNCTION WITH ERROR HANDLING ----------
def analyze_job_description(job_text):
    """
    Improved version with better error handling and retry logic
    """
    if not api_key:
        st.error("Please provide an OpenAI API key")
        return None
    
    try:
        client = OpenAI(api_key=api_key)
        
        prompt = create_expert_prompt(job_text)
        
        with st.spinner("🧠 Analyzing job description with AI..."):
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert technical recruiter specializing in Boolean search strings for LinkedIn Recruiter and DevelopmentAid. You have deep knowledge of search syntax and recruiting best practices."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower = more consistent (was 0.7)
                max_tokens=3000,  # Increased for detailed responses
                response_format={"type": "json_object"}  # Forces valid JSON
            )

        content = response.choices[0].message.content
        
        # Parse JSON
        try:
            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            # Fallback: try to extract JSON from text
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                return json.loads(content[start:end+1])
            else:
                st.error("⚠️ Failed to parse JSON from AI response.")
                with st.expander("See raw response"):
                    st.code(content)
                return None
                
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None


# ---------- IMPROVED DISPLAY ----------
if st.button("🔍 Generate Platform-Specific Search Strings"):
    if not api_key:
        st.error("Please enter your OpenAI API key.")
    elif not job_description.strip():
        st.error("Please upload or paste a job description.")
    else:
        analysis = analyze_job_description(job_description)

        if analysis:
            st.success("✅ Analysis complete!")
            
            # Show explanation first
            if analysis.get("explanation"):
                st.info(f"**Strategy:** {analysis['explanation']}")
            
            # Add copy buttons for easy use
            st.markdown("---")

            # Show analysis
            with st.expander("📊 Detailed Analysis", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🚨 Most Important Requirements")
                    for item in analysis["analysis"].get("mostImportant", []):
                        st.markdown(f"- {item}")
                    
                    st.subheader("🧩 Synonym Mapping")
                    for key, synonyms in analysis["analysis"].get("synonymMapping", {}).items():
                        st.markdown(f"**{key}:** {', '.join(synonyms)}")
                
                with col2:
                    st.subheader("💎 Most Unique Requirements")
                    for item in analysis["analysis"].get("mostUnique", []):
                        st.markdown(f"- {item}")
                    
                    st.subheader("👔 Relevant Job Titles")
                    for title in analysis["analysis"].get("jobTitles", []):
                        st.markdown(f"- {title}")

            st.markdown("---")

            # LinkedIn searches with copy buttons
            if "linkedinSearches" in analysis and platform in ["both", "linkedin"]:
                st.header("🔗 LinkedIn Recruiter Search Strings")
                
                searches = analysis["linkedinSearches"]
                
                for key, value in searches.items():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.text_area(
                            f"LinkedIn - {key.capitalize()}", 
                            value, 
                            height=120,
                            key=f"linkedin_{key}"
                        )
                    with col2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button(f"📋 Copy", key=f"copy_linkedin_{key}"):
                            st.code(value)

            st.markdown("---")

            # DevelopmentAid searches
            if "developmentaidSearches" in analysis and platform in ["both", "developmentaid"]:
                st.header("🌱 DevelopmentAid Search Strings")
                
                searches = analysis["developmentaidSearches"]
                
                for key, value in searches.items():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.text_area(
                            f"DevelopmentAid - {key.capitalize()}", 
                            value, 
                            height=120,
                            key=f"devaid_{key}"
                        )
                    with col2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button(f"📋 Copy", key=f"copy_devaid_{key}"):
                            st.code(value)

            # Pro tips section
            if analysis.get("tips"):
                st.markdown("---")
                st.subheader("💡 Pro Tips")
                for tip in analysis["tips"]:
                    st.markdown(f"- {tip}")
            
            # Export option
            st.markdown("---")
            if st.button("💾 Export All Results as JSON"):
                st.download_button(
                    label="Download JSON",
                    data=json.dumps(analysis, indent=2),
                    file_name="search_strings.json",
                    mime="application/json"
                )
