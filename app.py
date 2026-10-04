"""ClaimScout: an AI agent that finds money you're actually owed.

Run:  streamlit run app.py
"""
import streamlit as st

from agent.config import Settings
from agent.ics import deadlines_ics
from agent.models import UserProfile
from agent.pipeline import scout

st.set_page_config(page_title="ClaimScout", page_icon="🔎", layout="centered")

st.markdown("""
<style>
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:0.8rem;font-weight:600}
.likely{background:#DCFCE7;color:#166534}.maybe{background:#FEF3C7;color:#92400E}.unlikely{background:#F1F5F9;color:#475569}
</style>""", unsafe_allow_html=True)

st.title("🔎 ClaimScout")
st.caption("Finds open class action settlements you are actually part of, and money your state is holding for you. "
           "Powered by NVIDIA Nemotron on Nebius Token Factory, with live research by Tavily.")

settings = Settings()
if settings.demo_mode:
    st.info("Demo mode: API keys aren't set, so ClaimScout is using a saved snapshot and simple keyword matching. "
            "Add NEBIUS_API_KEY and TAVILY_API_KEY to run the live agent.")

with st.form("profile"):
    state = st.text_input("Your state", placeholder="Washington")
    brands = st.text_area("Products and brands you've bought", placeholder="Levoit air purifier, Kia Sportage, AirPods")
    stores = st.text_area("Stores, memberships and services you use", placeholder="CVS ExtraCare, Comcast, Amazon Prime")
    breaches = st.text_input("Any data breach letters or emails you've received?", placeholder="OneTouchPoint, MDLive")
    other = st.text_input("Anything else", placeholder="Used a tax prep site, had a gym membership...")
    st.caption("Nothing you type is stored. It's sent to the model for this search only.")
    go = st.form_submit_button("Find my money", type="primary", use_container_width=True)

if go:
    profile = UserProfile(state=state, brands_and_products=brands, stores_and_services=stores,
                          breach_notices=breaches, other_notes=other)
    with st.status("Scouting...", expanded=True) as status:
        try:
            result = scout(profile, settings, log=st.write)
        except Exception as e:
            status.update(label="Something went wrong", state="error")
            st.error(f"{type(e).__name__}: {e}")
            st.stop()
        status.update(label=f"Checked {result.settlements_found} open settlements", state="complete", expanded=False)

    shown = [m for m in result.matches if m.verdict != "unlikely"]
    st.subheader(f"{len(shown)} settlement{'s' if len(shown) != 1 else ''} worth a look")
    if not shown:
        st.write("Nothing matched what you told us. Try adding more products, stores or services.")
    for m in shown:
        s = m.settlement
        with st.container(border=True):
            st.markdown(f"<span class='badge {m.verdict}'>{m.verdict.upper()} ELIGIBLE</span>", unsafe_allow_html=True)
            st.markdown(f"**{s.name}**")
            c1, c2 = st.columns([3, 2])
            c1.markdown(f"💵 **Payout:** {s.payout or 'See site'}")
            c2.markdown(f"📅 **Deadline:** {s.deadline or 'See site'}")
            st.write(m.reason)
            if m.what_to_check:
                st.markdown(f"**Confirm before filing:** {m.what_to_check}")
            if s.proof_required:
                st.caption(f"Proof: {s.proof_required}")
            link = s.claim_url or s.source_url
            if link:
                st.link_button("Open claim page", link)

    if shown:
        st.download_button("Add deadlines to my calendar (.ics)", deadlines_ics(shown),
                           file_name="claimscout-deadlines.ics", mime="text/calendar")

    st.divider()
    st.markdown(f"**Also check unclaimed property.** States hold forgotten paychecks, refunds and deposits. "
                f"Search free on the official site: [{result.unclaimed_property_url}]({result.unclaimed_property_url})")
    st.caption("A claim is a statement made under penalty of perjury. Only file for settlements you are really part of. "
               "ClaimScout is not a law firm and doesn't give legal advice.")
