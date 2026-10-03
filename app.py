import streamlit as st
import sqlite3
import hashlib
import random
import csv
import io
from datetime import datetime

import sympy as sp
import requests

DB = "tutor.db"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3:1.7b"

st.set_page_config(
    page_title="AI Morocco Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------- DATABASE ----------------

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    cur = c.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        xp INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS exercises(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        chapter TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        explanation TEXT NOT NULL
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attempts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        exercise_id INTEGER NOT NULL,
        answer_given TEXT,
        correct INTEGER NOT NULL,
        created_at TEXT NOT NULL
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS progress(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        chapter TEXT NOT NULL,
        attempts INTEGER DEFAULT 0,
        correct INTEGER DEFAULT 0,
        UNIQUE(user_id, chapter)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS lessons(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        chapter TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        test_type TEXT NOT NULL,
        score INTEGER NOT NULL,
        total INTEGER NOT NULL,
        created_at TEXT NOT NULL
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS badges(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        badge TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(user_id,badge)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS activity(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")

    admin = hashlib.sha256("admin123".encode()).hexdigest()
    cur.execute("SELECT id FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("""
        INSERT INTO users(username,password,is_admin,xp,created_at)
        VALUES(?,?,?,?,?)
        """, ("admin", admin, 1, 0, datetime.now().isoformat()))

    c.commit()
    c.close()

def seed():
    c = db()
    cur = c.cursor()

    if cur.execute("SELECT COUNT(*) FROM exercises").fetchone()[0] == 0:
        exercises = [
            ("Math","Limites","Easy","Calculer lim(x→2) (x²-4)/(x-2).","4","Factoriser x²-4=(x-2)(x+2), puis la limite vaut 4."),
            ("Math","Limites","Medium","Calculer lim(x→0) sin(x)/x.","1","C'est une limite remarquable."),
            ("Math","Limites","Hard","Calculer lim(x→∞) (2x²+1)/(x²+3).","2","Diviser numérateur et dénominateur par x²."),
            ("Math","Dérivation","Easy","Calculer la dérivée de f(x)=x²+3x+2.","2x+3","Dériver chaque terme."),
            ("Math","Dérivation","Medium","Calculer f'(x) pour f(x)=x³-5x²+2x.","3x²-10x+2","Appliquer les règles de dérivation."),
            ("Math","Dérivation","Hard","Calculer la dérivée de f(x)=x² sin(x).","2xsin(x)+x²cos(x)","Utiliser la règle du produit."),
            ("Math","Équations","Easy","Résoudre 2x+6=0.","-3","2x=-6 donc x=-3."),
            ("Math","Équations","Medium","Résoudre x²-5x+6=0.","2,3","Factoriser (x-2)(x-3)."),
            ("Math","Équations","Hard","Résoudre x²-4x-5=0.","-1,5","Factoriser (x-5)(x+1)."),
            ("Math","Primitives","Easy","Donner une primitive de f(x)=2x.","x²","La dérivée de x² est 2x."),
            ("Math","Primitives","Medium","Donner une primitive de f(x)=3x².","x³","La dérivée de x³ est 3x²."),
            ("Math","Suites numériques","Easy","u1=5 et r=3. Calculer u4.","14","u4=u1+3r=14."),
            ("Math","Suites numériques","Medium","u1=2 et q=3. Calculer u4.","54","u4=2×3³=54."),
            ("Math","Probabilités","Easy","Une pièce équilibrée est lancée. P(pile) ?","1/2","Deux issues équiprobables."),
            ("Math","Nombres complexes","Easy","Calculer i².","-1","Par définition i²=-1."),
            ("Math","Arithmétique","Easy","Calculer PGCD(18,24).","6","Le plus grand diviseur commun est 6."),
            ("Math","Étude de fonctions","Medium","Si f'(x)>0 sur un intervalle, f est-elle croissante ?","croissante","Une dérivée positive implique une croissance stricte."),
            ("Physics","Mécanique","Easy","100 m en 20 s. Vitesse moyenne ?","5","v=d/t=5 m/s."),
            ("Physics","Mécanique","Medium","m=2 kg et a=3 m/s². Calculer F.","6","F=ma=6 N."),
            ("Physics","Électricité","Easy","U=12 V et R=4 Ω. Calculer I.","3","I=U/R=3 A."),
            ("Physics","Électricité","Medium","U=10 V et I=2 A. Calculer R.","5","R=U/I=5 Ω."),
            ("Physics","Énergie","Easy","m=2 kg et v=3 m/s. Calculer Ec.","9","Ec=½mv²=9 J."),
            ("Physics","Ondes","Easy","Une onde a f=2 Hz. Sa période ?","0.5","T=1/f=0.5 s."),
        ]
        cur.executemany("""
        INSERT INTO exercises(subject,chapter,difficulty,question,answer,explanation)
        VALUES(?,?,?,?,?,?)
        """, exercises)

    if cur.execute("SELECT COUNT(*) FROM lessons").fetchone()[0] == 0:
        lessons = [
            ("Math","Limites","Introduction aux limites",
             "Une limite décrit le comportement d'une fonction lorsque x se rapproche d'une valeur.\n\nMéthode :\n1. Remplacer directement si possible.\n2. Si forme indéterminée, factoriser ou simplifier.\n3. Utiliser les limites remarquables."),
            ("Math","Dérivation","Les dérivées",
             "(x^n)' = n x^(n-1)\n\n(sin x)' = cos x\n\n(cos x)' = -sin x\n\nLa dérivée permet d'étudier les variations."),
            ("Math","Suites numériques","Suites arithmétiques et géométriques",
             "Suite arithmétique : u_n = u_1 + (n-1)r\n\nSuite géométrique : u_n = u_1 q^(n-1)."),
            ("Math","Probabilités","Bases des probabilités",
             "Pour des événements équiprobables : P(A)=cas favorables/cas possibles."),
            ("Physics","Mécanique","Deuxième loi de Newton",
             "F = ma\n\nF en Newton, m en kg et a en m/s²."),
            ("Physics","Électricité","Loi d'Ohm",
             "U = RI\n\nDonc I=U/R et R=U/I."),
        ]
        cur.executemany("""
        INSERT INTO lessons(subject,chapter,title,content)
        VALUES(?,?,?,?)
        """, lessons)

    c.commit()
    c.close()

init_db()
seed()

# ---------------- HELPERS ----------------

def hp(x):
    return hashlib.sha256(x.encode()).hexdigest()

def now():
    return datetime.now().isoformat(timespec="seconds")

def log(action):
    if st.session_state.get("user_id"):
        c=db()
        c.execute("INSERT INTO activity(user_id,action,created_at) VALUES(?,?,?)",
                  (st.session_state.user_id, action, now()))
        c.commit(); c.close()

def add_xp(n):
    c=db()
    c.execute("UPDATE users SET xp=xp+? WHERE id=?", (n,st.session_state.user_id))
    c.commit(); c.close()

def user():
    c=db()
    r=c.execute("SELECT * FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
    c.close()
    return r

def normalize(s):
    return str(s).lower().replace(" ","").replace(",",".").replace("−","-").replace("×","*").strip()

def match(a,b):
    if normalize(a)==normalize(b):
        return True
    try:
        return sp.simplify(sp.sympify(normalize(a))-sp.sympify(normalize(b)))==0
    except:
        return False

def stats():
    c=db()
    total=c.execute("SELECT COUNT(*) FROM attempts WHERE user_id=?", (st.session_state.user_id,)).fetchone()[0]
    correct=c.execute("SELECT COUNT(*) FROM attempts WHERE user_id=? AND correct=1", (st.session_state.user_id,)).fetchone()[0]
    xp=c.execute("SELECT xp FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()[0]
    c.close()
    return total,correct,(correct/total*100 if total else 0),xp

def weakest():
    c=db()
    rows=c.execute("""
    SELECT chapter,attempts,correct FROM progress
    WHERE user_id=? AND attempts>0
    """,(st.session_state.user_id,)).fetchall()
    c.close()
    if not rows: return None
    return min(rows,key=lambda r:r["correct"]/r["attempts"])["chapter"]

def update_progress(ch, ok):
    c=db()
    c.execute("""
    INSERT INTO progress(user_id,chapter,attempts,correct)
    VALUES(?,?,1,?)
    ON CONFLICT(user_id,chapter)
    DO UPDATE SET attempts=attempts+1, correct=correct+excluded.correct
    """,(st.session_state.user_id,ch,1 if ok else 0))
    c.commit(); c.close()

def badges():
    total,correct,acc,xp=stats()
    possible=[]
    if total>=1: possible.append("🚀 First Exercise")
    if correct>=10: possible.append("🔥 10 Correct")
    if correct>=25: possible.append("🏆 25 Correct")
    if acc>=80 and total>=10: possible.append("🎯 80% Accuracy")
    if xp>=500: possible.append("⭐ 500 XP")
    c=db()
    for b in possible:
        c.execute("INSERT OR IGNORE INTO badges(user_id,badge,created_at) VALUES(?,?,?)",
                  (st.session_state.user_id,b,now()))
    c.commit(); c.close()

def ai(prompt):
    try:
        r=requests.post(OLLAMA_URL,json={
            "model":MODEL,
            "messages":[
                {"role":"system","content":
                 "You are AI Morocco Tutor for Moroccan 2BAC Sciences Mathématiques students. "
                 "Answer in simple French. Explain step by step. Do not only give the final answer. "
                 "Use school-level methods and verify calculations."},
                {"role":"user","content":prompt}
            ],
            "stream":False
        },timeout=90)
        return r.json()["message"]["content"]
    except:
        return "⚠️ Ollama is not running. Start: ollama run qwen3:1.7b"

def adaptive_exercise(subject, difficulty=None):
    c=db()
    weak=weakest()
    q="SELECT * FROM exercises WHERE subject=?"
    p=[subject]
    if weak:
        q += " ORDER BY CASE WHEN chapter=? THEN 0 ELSE 1 END, RANDOM()"
        p.append(weak)
    else:
        q += " ORDER BY RANDOM()"
    if difficulty:
        # Keep difficulty filter while retaining adaptive chapter preference.
        q="SELECT * FROM exercises WHERE subject=? AND difficulty=?"
        p=[subject,difficulty]
        if weak:
            q += " ORDER BY CASE WHEN chapter=? THEN 0 ELSE 1 END, RANDOM()"
            p.append(weak)
        else:
            q += " ORDER BY RANDOM()"
    row=c.execute(q+" LIMIT 1",p).fetchone()
    c.close()
    return dict(row) if row else None

# ---------------- SESSION ----------------

for k,v in {
    "logged":False,"user_id":None,"username":None,"admin":False,
    "exercise":None,"test_questions":[],"test_i":0,"test_score":0,"test_type":None
}.items():
    if k not in st.session_state: st.session_state[k]=v

# ---------------- AUTH ----------------

if not st.session_state.logged:
    st.title("🎓 AI Morocco Tutor")
    st.caption("Adaptive learning platform for 2BAC Sciences Mathématiques")

    a,b=st.tabs(["🔐 Login","📝 Create Account"])

    with a:
        u=st.text_input("Username",key="login_u")
        p=st.text_input("Password",type="password",key="login_p")
        if st.button("Login",use_container_width=True):
            c=db()
            r=c.execute("SELECT * FROM users WHERE username=? AND password=?",(u,hp(p))).fetchone()
            c.close()
            if r:
                st.session_state.logged=True
                st.session_state.user_id=r["id"]
                st.session_state.username=r["username"]
                st.session_state.admin=bool(r["is_admin"])
                st.rerun()
            else: st.error("Invalid username or password.")

    with b:
        u=st.text_input("New username",key="new_u")
        p=st.text_input("New password",type="password",key="new_p")
        if st.button("Create Account",use_container_width=True):
            if len(u)<3 or len(p)<4: st.error("Username: 3+ characters. Password: 4+ characters.")
            else:
                try:
                    c=db()
                    c.execute("INSERT INTO users(username,password,created_at) VALUES(?,?,?)",(u,hp(p),now()))
                    c.commit(); c.close()
                    st.success("Account created.")
                except sqlite3.IntegrityError: st.error("Username already exists.")
    st.stop()

# ---------------- SIDEBAR ----------------

me=user()
total,correct,accuracy,xp=stats()
level=xp//100+1

st.sidebar.title("🎓 AI Morocco Tutor")
st.sidebar.write(f"👤 **{me['username']}**")
st.sidebar.metric("Level",level)
st.sidebar.progress(min((xp%100)/100,1.0))
st.sidebar.caption(f"{xp} XP")

pages=[
"🏠 Dashboard","🧠 Personal Tutor","🤖 AI Tutor","📚 Lessons",
"📖 Curriculum","🎯 Adaptive Practice","📝 Tests","🏆 Achievements",
"📊 Research","🧮 Equation Solver","📐 Derivative","∫ Integral","∞ Limit"
]
if st.session_state.admin: pages.append("⚙️ Admin")

page=st.sidebar.radio("Navigation",pages)

if st.sidebar.button("Logout",use_container_width=True):
    st.session_state.clear()
    st.rerun()

# ---------------- DASHBOARD ----------------

if page=="🏠 Dashboard":
    st.title("🏠 Dashboard")
    a,b,c,d=st.columns(4)
    a.metric("Exercises",total)
    b.metric("Correct",correct)
    c.metric("Accuracy",f"{accuracy:.1f}%")
    d.metric("XP",xp)

    st.markdown("---")
    w=weakest()
    st.subheader("🎯 Adaptive Recommendation")
    if w:
        st.info(f"Your weakest chapter is **{w}**. Practice it next.")
    else:
        st.info("Complete your first exercises to activate adaptive learning.")

    c=db()
    rows=c.execute("""
    SELECT chapter,attempts,correct FROM progress
    WHERE user_id=? ORDER BY attempts DESC
    """,(st.session_state.user_id,)).fetchall()
    acts=c.execute("""
    SELECT action,created_at FROM activity WHERE user_id=?
    ORDER BY id DESC LIMIT 8
    """,(st.session_state.user_id,)).fetchall()
    c.close()

    if rows:
        st.subheader("📊 Chapter Performance")
        for r in rows:
            s=r["correct"]/r["attempts"]*100
            st.write(f"**{r['chapter']}** — {r['correct']}/{r['attempts']} ({s:.0f}%)")
            st.progress(s/100)

    st.subheader("🕒 Recent Activity")
    for x in acts: st.write(f"• {x['action']}")

# ---------------- PERSONAL TUTOR ----------------

elif page=="🧠 Personal Tutor":
    st.title("🧠 Personal Tutor")
    w=weakest()
    if not w:
        st.info("Do some exercises first.")
    else:
        st.metric("Weakest chapter",w)
        if st.button("Generate 7-Day Plan",use_container_width=True):
            st.markdown(ai(f"""
Create a realistic 7-day plan for a Moroccan 2BAC SM student.
Weakest chapter: {w}
Accuracy: {accuracy:.1f}%
Include daily revision, exercises and one test.
"""))
            add_xp(5)
            log("Generated a 7-day study plan")

# ---------------- AI ----------------

elif page=="🤖 AI Tutor":
    st.title("🤖 AI Tutor")
    q=st.text_area("Ask your question",height=180)
    if st.button("Ask AI",use_container_width=True) and q.strip():
        with st.spinner("AI is thinking..."):
            st.markdown(ai(q))
        add_xp(5); log("Used AI Tutor")

# ---------------- LESSONS ----------------

elif page=="📚 Lessons":
    st.title("📚 Lessons")
    c=db()
    rows=c.execute("SELECT * FROM lessons ORDER BY subject,chapter").fetchall()
    c.close()
    for r in rows:
        with st.expander(f"📘 {r['subject']} — {r['title']}"):
            st.markdown(r["content"])

# ---------------- CURRICULUM ----------------

elif page=="📖 Curriculum":
    st.title("📖 Curriculum Map")
    curriculum={
        "Math":["Limites","Dérivation","Étude de fonctions","Primitives","Intégrales","Suites numériques","Probabilités","Nombres complexes","Arithmétique","Géométrie"],
        "Physics":["Mécanique","Électricité","Ondes","Énergie"],
        "Chemistry":["Transformations chimiques","Cinétique","Équilibres","Acide-base","Oxydoréduction"]
    }
    for s,chs in curriculum.items():
        st.subheader(s)
        st.write(" • ".join(chs))

# ---------------- ADAPTIVE PRACTICE ----------------

elif page=="🎯 Adaptive Practice":
    st.title("🎯 Adaptive Practice")
    st.caption("The system prioritizes your weakest chapter.")

    subject=st.selectbox("Subject",["Math","Physics"])
    diff=st.selectbox("Difficulty",["All","Easy","Medium","Hard"])

    if st.button("🎲 Generate Adaptive Exercise",use_container_width=True):
        st.session_state.exercise=adaptive_exercise(subject,None if diff=="All" else diff)
        st.rerun()

    ex=st.session_state.exercise
    if ex:
        st.markdown("---")
        st.subheader(f"{ex['chapter']} • {ex['difficulty']}")
        st.write(ex["question"])
        ans=st.text_input("Your answer",key=f"ans_{ex['id']}")
        if st.button("Check Answer",use_container_width=True):
            ok=match(ans,ex["answer"])
            c=db()
            c.execute("""
            INSERT INTO attempts(user_id,exercise_id,answer_given,correct,created_at)
            VALUES(?,?,?,?,?)
            """,(st.session_state.user_id,ex["id"],ans,1 if ok else 0,now()))
            c.commit(); c.close()
            update_progress(ex["chapter"],ok)
            if ok:
                st.success("✅ Correct! +20 XP")
                add_xp(20)
            else:
                st.error(f"❌ Correct answer: {ex['answer']}")
            with st.expander("📖 Explanation"):
                st.write(ex["explanation"])
            badges()
            log(f"Completed {ex['chapter']}")
    else:
        st.info("Generate an exercise.")

# ---------------- TESTS ----------------

elif page=="📝 Tests":
    st.title("📝 Pre-Test / Post-Test")
    st.write("Use the same system to measure learning improvement.")

    if not st.session_state.test_questions:
        typ=st.selectbox("Test",["Pre-Test","Post-Test"])
        if st.button("Start Test",use_container_width=True):
            c=db()
            qs=c.execute("SELECT * FROM exercises ORDER BY RANDOM() LIMIT 10").fetchall()
            c.close()
            st.session_state.test_questions=[dict(x) for x in qs]
            st.session_state.test_i=0
            st.session_state.test_score=0
            st.session_state.test_type=typ
            st.rerun()
    else:
        i=st.session_state.test_i
        qs=st.session_state.test_questions
        if i<len(qs):
            q=qs[i]
            st.progress(i/len(qs))
            st.subheader(f"Question {i+1}/{len(qs)}")
            st.write(q["question"])
            ans=st.text_input("Answer",key=f"test_{i}")
            if st.button("Submit",use_container_width=True):
                if match(ans,q["answer"]):
                    st.session_state.test_score+=1
                st.session_state.test_i+=1
                st.rerun()
        else:
            score=st.session_state.test_score
            totalq=len(qs)
            st.success(f"{st.session_state.test_type}: {score}/{totalq}")
            c=db()
            c.execute("INSERT INTO tests(user_id,test_type,score,total,created_at) VALUES(?,?,?,?,?)",
                      (st.session_state.user_id,st.session_state.test_type,score,totalq,now()))
            c.commit(); c.close()
            add_xp(50)
            st.session_state.test_questions=[]
            if st.button("Finish"):
                st.rerun()

# ---------------- BADGES ----------------

elif page=="🏆 Achievements":
    st.title("🏆 Achievements")
    badges()
    c=db()
    rows=c.execute("SELECT badge,created_at FROM badges WHERE user_id=? ORDER BY id DESC",
                   (st.session_state.user_id,)).fetchall()
    c.close()
    if rows:
        for r in rows: st.success(r["badge"])
    else: st.info("Complete exercises to unlock badges.")

# ---------------- RESEARCH ----------------

elif page=="📊 Research":
    st.title("📊 Learning Analytics")
    a,b,c,d=st.columns(4)
    a.metric("Exercises",total)
    b.metric("Accuracy",f"{accuracy:.1f}%")
    d.metric("XP",xp)

    conn=db()
    tests=conn.execute("SELECT test_type,score,total,created_at FROM tests WHERE user_id=? ORDER BY id",
                       (st.session_state.user_id,)).fetchall()
    attempts=conn.execute("""
    SELECT e.subject,e.chapter,e.difficulty,e.question,a.answer_given,a.correct,a.created_at
    FROM attempts a JOIN exercises e ON a.exercise_id=e.id
    WHERE a.user_id=?
    """,(st.session_state.user_id,)).fetchall()
    conn.close()

    st.subheader("🧪 Pre/Post Results")
    for t in tests:
        pct=t["score"]/t["total"]*100
        st.write(f"**{t['test_type']}** — {t['score']}/{t['total']} ({pct:.0f}%)")
        st.progress(pct/100)

    st.subheader("📥 Export Learning Data")
    if attempts:
        out=io.StringIO()
        w=csv.writer(out)
        w.writerow(["subject","chapter","difficulty","question","answer_given","correct","created_at"])
        for r in attempts:
            w.writerow([r[k] for k in ["subject","chapter","difficulty","question","answer_given","correct","created_at"]])
        st.download_button("Download CSV",out.getvalue(),"learning_data.csv","text/csv")

    st.info("For real research use, collect consent and analyze only anonymized/aggregate student data.")

# ---------------- TOOLS ----------------

elif page=="🧮 Equation Solver":
    st.title("🧮 Equation Solver")
    eq=st.text_input("Equation","x^2 - 5*x + 6 = 0")
    var=st.text_input("Variable","x")
    if st.button("Solve",use_container_width=True):
        try:
            x=sp.symbols(var)
            l,r=eq.split("=")
            sol=sp.solve(sp.sympify(l.replace("^","**"))-sp.sympify(r.replace("^","**")),x)
            st.success(str(sol))
        except Exception as e: st.error(str(e))

elif page=="📐 Derivative":
    st.title("📐 Derivative")
    e=st.text_input("f(x)","x^3+2*x^2")
    if st.button("Calculate",use_container_width=True):
        try:
            x=sp.symbols("x")
            r=sp.diff(sp.sympify(e.replace("^","**")),x)
            st.latex("f'(x)="+sp.latex(r))
        except Exception as er: st.error(str(er))

elif page=="∫ Integral":
    st.title("∫ Integral")
    e=st.text_input("f(x)","3*x^2")
    if st.button("Calculate",use_container_width=True):
        try:
            x=sp.symbols("x")
            r=sp.integrate(sp.sympify(e.replace("^","**")),x)
            st.latex("\\int f(x)dx="+sp.latex(r)+"+C")
        except Exception as er: st.error(str(er))

elif page=="∞ Limit":
    st.title("∞ Limit")
    e=st.text_input("f(x)","(x^2-4)/(x-2)")
    p=st.text_input("x →","2")
    if st.button("Calculate",use_container_width=True):
        try:
            x=sp.symbols("x")
            r=sp.limit(sp.sympify(e.replace("^","**")),x,sp.sympify(p))
            st.latex("\\lim_{x\\to "+sp.latex(sp.sympify(p))+"}f(x)="+sp.latex(r))
        except Exception as er: st.error(str(er))

# ---------------- ADMIN ----------------

elif page=="⚙️ Admin":
    st.title("⚙️ Admin Panel")
    tabs=st.tabs(["📚 Exercises","➕ Add Exercise","📘 Lessons","👥 Users","📊 Analytics"])

    with tabs[0]:
        c=db()
        rows=c.execute("SELECT * FROM exercises ORDER BY id DESC").fetchall()
        c.close()
        for r in rows:
            with st.expander(f"#{r['id']} — {r['subject']} — {r['chapter']}"):
                st.write(r["question"])
                st.caption("Answer: "+r["answer"])
                if st.button("Delete",key=f"del_{r['id']}"):
                    c=db(); c.execute("DELETE FROM exercises WHERE id=?",(r["id"],)); c.commit(); c.close()
                    st.rerun()

    with tabs[1]:
        s=st.selectbox("Subject",["Math","Physics","Chemistry"],key="as")
        ch=st.text_input("Chapter")
        di=st.selectbox("Difficulty",["Easy","Medium","Hard"])
        q=st.text_area("Question")
        an=st.text_input("Answer")
        ex=st.text_area("Explanation")
        if st.button("Add Exercise",use_container_width=True):
            if q and an and ch:
                c=db()
                c.execute("INSERT INTO exercises(subject,chapter,difficulty,question,answer,explanation) VALUES(?,?,?,?,?,?)",
                          (s,ch,di,q,an,ex))
                c.commit(); c.close(); st.success("Added.")
            else: st.error("Fill the required fields.")

    with tabs[2]:
        s=st.selectbox("Subject",["Math","Physics","Chemistry"],key="ls")
        ch=st.text_input("Chapter",key="lc")
        title=st.text_input("Title")
        content=st.text_area("Content",height=250)
        if st.button("Add Lesson",use_container_width=True):
            c=db()
            c.execute("INSERT INTO lessons(subject,chapter,title,content) VALUES(?,?,?,?)",(s,ch,title,content))
            c.commit(); c.close(); st.success("Lesson added.")

    with tabs[3]:
        c=db()
        rows=c.execute("SELECT id,username,xp,created_at FROM users ORDER BY id").fetchall()
        c.close()
        for r in rows:
            st.write(f"👤 {r['username']} | XP {r['xp']} | ID {r['id']}")

    with tabs[4]:
        c=db()
        users=c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        exs=c.execute("SELECT COUNT(*) FROM exercises").fetchone()[0]
        at=c.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        co=c.execute("SELECT COUNT(*) FROM attempts WHERE correct=1").fetchone()[0]
        c.close()
        a,b,c,d=st.columns(4)
        a.metric("Users",users); b.metric("Exercises",exs); c.metric("Attempts",at)
        d.metric("Global Accuracy",f"{co/at*100:.1f}%" if at else "0%")

st.markdown("---")
st.caption("AI Morocco Tutor • Adaptive Learning • 2BAC Sciences Mathématiques")
