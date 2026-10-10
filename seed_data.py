"""Generates FICTIONAL demo metadata (not real KMRL documents). Deterministic."""
import csv, datetime as dt, pathlib
D = {"OPS": "Operations", "SIG": "Signalling & Telecom", "EM": "Electrical & Mechanical",
     "CIV": "Civil & Track", "SAF": "Safety & Security", "PRO": "Procurement", "ADM": "Administration"}
P = {"A": "Phase 1 Operations", "B": "Phase 1A Extension", "C": "Depot Modernisation",
     "D": "Safety Upgrade Programme", "E": "Digital Asset Management"}
# title | dept | project | type | topics | owner role
ROWS = """Train Operations Manual|OPS|A|Procedure|train operations;passenger safety|Operations Manager
Station Control Room Handbook|OPS|A|Procedure|train operations;station maintenance|Station Controller
Daily Service Performance Report|OPS|A|Report|train operations;audit|Operations Manager
Platform Crowd Management Plan|OPS|B|Plan|passenger safety;crowd management|Station Controller
Signalling Maintenance Schedule|SIG|A|Schedule|signalling;asset management|Signalling Engineer
CBTC Fault Log Summary|SIG|A|Report|signalling;incident reporting|Signalling Engineer
Telecom Network Inspection Record|SIG|B|Record|telecom;asset management|Telecom Engineer
Signalling Vendor Service Agreement|SIG|E|Contract|signalling;vendor contracts|Procurement Officer
Rolling Stock Inspection Checklist|EM|C|Checklist|rolling stock;asset management|Maintenance Engineer
Traction Power Maintenance Report|EM|A|Report|power supply;asset management|Electrical Engineer
Depot Equipment Overhaul Plan|EM|C|Plan|rolling stock;station maintenance|Maintenance Engineer
Escalator and Lift Maintenance Log|EM|B|Record|station maintenance;asset management|Maintenance Engineer
Substation Safety Inspection|EM|D|Record|power supply;fire safety|Electrical Engineer
Track Inspection Record Q1|CIV|A|Record|track inspection;asset management|Track Engineer
Viaduct Structural Health Report|CIV|B|Report|structural health;audit|Civil Engineer
Track Maintenance Procedure|CIV|A|Procedure|track inspection;station maintenance|Track Engineer
Depot Civil Works Progress Report|CIV|C|Report|structural health;project progress|Project Manager
Emergency Response Plan|SAF|D|Plan|emergency response;passenger safety|Safety Officer
Fire Safety Audit Report|SAF|D|Report|fire safety;audit|Safety Officer
Incident Summary Report Q2|SAF|A|Report|incident reporting;passenger safety|Safety Officer
Evacuation Drill Procedure|SAF|D|Procedure|emergency response;training|Safety Officer
Staff Safety Training Syllabus|SAF|D|Plan|training;passenger safety|Training Coordinator
Security Screening Guidelines|SAF|A|Guideline|passenger safety;crowd management|Safety Officer
Tender Notice: Track Fittings|PRO|B|Tender|tendering;track inspection|Procurement Officer
Vendor Evaluation Report|PRO|C|Report|vendor contracts;tendering|Procurement Officer
Spare Parts Procurement Policy|PRO|E|Policy|vendor contracts;asset management|Procurement Officer
Rolling Stock Spares Contract|PRO|C|Contract|vendor contracts;rolling stock|Procurement Officer
Asset Register Standard|ADM|E|Standard|asset management;audit|Asset Manager
Digital Document Retention Policy|ADM|E|Policy|audit;document control|Records Officer
Project Progress Review Minutes|ADM|B|Minutes|project progress;audit|Project Manager
Annual Internal Audit Summary|ADM|E|Report|audit;incident reporting|Records Officer
Document Control Procedure|ADM|E|Procedure|document control;asset management|Records Officer""".splitlines()
def build():
    docs = []
    for i, line in enumerate(ROWS):
        t, d, p, ty, tp, role = line.split("|")
        docs.append(dict(document_id=f"DOC-{i+1:03d}", title=t, department=D[d], project=P[p],
                         date=(dt.date(2024, 1, 8) + dt.timedelta(days=11 * i)).isoformat(),
                         document_type=ty, topics=tp, references="", owner_role=role))
    for i, d in enumerate(docs):  # reference up to 2 EARLIER docs that share a topic
        mine = set(d["topics"].split(";"))
        refs = [e["document_id"] for e in docs[:i] if mine & set(e["topics"].split(";"))]
        d["references"] = ";".join(refs[-2:])
    return docs
if __name__ == "__main__":
    out = pathlib.Path(__file__).resolve().parents[1] / "data" / "sample_documents.csv"
    docs = build()
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(docs[0])); w.writeheader(); w.writerows(docs)
    print(f"Wrote {len(docs)} synthetic documents to {out}")
