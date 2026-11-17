"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { LangSwitch, useLang } from "./lang";
import { Logo } from "./Logo";
import HeroBoard from "./HeroBoard";
import { COPY, Copy } from "../lib/landing-copy";
import { BRAND, SUPPORT } from "../lib/brand";
import { supabase } from "../lib/supabase";
import { tr } from "../lib/i18n";

const SIGNUP = "/login?mode=signup";

function spot(e: React.MouseEvent<HTMLElement>) {
  const r = e.currentTarget.getBoundingClientRect();
  e.currentTarget.style.setProperty("--mx", `${e.clientX - r.left}px`);
  e.currentTarget.style.setProperty("--my", `${e.clientY - r.top}px`);
}

/* ---------- barra in alto ---------- */
function Nav({ c }: { c: Copy }) {
  const { lang } = useLang();
  const [logged, setLogged] = useState(false);
  useEffect(() => { supabase.auth.getSession().then(({ data }) => setLogged(!!data.session)); }, []);
  return (
    <header className="lp-nav">
      <div className="lp-wrap lp-nav-in">
        <Link href="/" aria-label={BRAND}><Logo size={34} /></Link>
        <nav className="lp-links" aria-label="Sections">
          <a href="#features">{c.nav.features}</a><a href="#how">{c.nav.how}</a><a href="#pricing">{c.nav.pricing}</a><a href="#faq">{c.nav.faq}</a>
        </nav>
        <div className="lp-nav-r">
          <LangSwitch />
          {logged ? <Link className="btn btn-primary btn-sm" href="/dashboard">{tr("openApp", lang)}</Link>
                  : <Link className="btn btn-ghost btn-sm" href="/login">{c.nav.login}</Link>}
        </div>
      </div>
    </header>
  );
}

/* ---------- hero ---------- */
function Hero({ c }: { c: Copy }) {
  const [san, setSan] = useState("");
  return (
    <section className="lp-hero">
      <div className="lp-aurora" aria-hidden="true"><i /><i /></div>
      <div className="lp-wrap lp-hero-grid">
        <div className="lp-hero-copy">
          <h1>{c.hero.title}<span className="lp-brill" aria-hidden="true">!!</span></h1>
          <p className="lp-lead">{c.hero.sub}</p>
          <div className="lp-cta-row">
            <Link href={SIGNUP} className="btn btn-primary btn-lg">{c.hero.cta}</Link>
            <a href="#how" className="btn btn-ghost btn-lg">{c.hero.cta2}</a>
          </div>
          <p className="lp-note">{c.hero.note}</p>
        </div>
        <div className="lp-hero-board">
          <div className="lp-board-glow" aria-hidden="true" />
          <HeroBoard onMove={(s) => setSan(s)} />
          <div className="lp-float lp-float-a" aria-hidden="true">
            <span className="lp-tag">{c.hero.example}</span>
            <b>{c.hero.cardTitle}</b>
            <p>{c.hero.cardText}</p>
          </div>
          <div className="lp-float lp-float-b" aria-live="off"><span className="lp-san">{san || "e4"}</span></div>
        </div>
      </div>
    </section>
  );
}

function Marquee({ c }: { c: Copy }) {
  const items = [...c.marquee, ...c.marquee];
  return (
    <div className="lp-marq" aria-hidden="true">
      <div className="lp-marq-track">{items.map((x, i) => <span key={i}>{x}</span>)}</div>
    </div>
  );
}

/* ---------- come funziona: la scena a destra cambia mentre scorri ---------- */
function VisConnect({ c }: { c: Copy }) {
  return (
    <div className="vis">
      <b>{c.vis.accounts}</b>
      <div className="vis-row"><span className="avatar">MC</span><span className="dot lichess" />Lichess<em>DrNykterstein</em></div>
      <div className="vis-row"><span className="avatar">MC</span><span className="dot chesscom" />Chess.com<em>MagnusCarlsen</em></div>
      <div className="vis-row add"><span>{c.vis.add}</span></div>
    </div>
  );
}
function VisAnalyze({ c }: { c: Copy }) {
  const rows: [string, string, string][] = [["12. Nf3", "", ""], ["13. Bxh7", "bad", c.vis.blunder], ["14. Qe2", "", ""], ["15. Rd1", "mid", c.vis.mistake], ["16. h3", "low", c.vis.inaccuracy], ["17. Nd4", "ok", c.vis.best]];
  return (
    <div className="vis">
      <div className="vis-row"><b>{c.vis.accuracy}</b><em className="big">87%</em></div>
      <div className="meter"><i style={{ width: "87%" }} /></div>
      {rows.map(([m, k, l]) => <div key={m} className="vis-move"><span>{m}</span>{k && <span className={"pill " + k}>{l}</span>}</div>)}
    </div>
  );
}
function VisLesson({ c }: { c: Copy }) {
  const it = c.demo.items[0];
  return (
    <div className="vis">
      <span className="lp-tag">{c.demo.example}</span>
      <p><b>{c.demo.heads[0]}</b><br />{it.error}</p>
      <p><b>{c.demo.heads[1]}</b><br />{it.idea}</p>
    </div>
  );
}

function How({ c }: { c: Copy }) {
  const [active, setActive] = useState(0);
  const refs = useRef<(HTMLLIElement | null)[]>([]);
  useEffect(() => {
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) setActive(Number((e.target as HTMLElement).dataset.i)); }), { rootMargin: "-42% 0px -42% 0px" });
    refs.current.forEach((el) => el && io.observe(el));
    return () => io.disconnect();
  }, []);
  const vis = [<VisConnect key="a" c={c} />, <VisAnalyze key="b" c={c} />, <VisLesson key="c" c={c} />];
  return (
    <section id="how" className="lp-section">
      <div className="lp-wrap">
        <h2 className="lp-h2">{c.how.title}</h2>
        <p className="lp-sub">{c.how.sub}</p>
        <div className="lp-how">
          <ol className="lp-steps">
            {c.how.steps.map((s, i) => (
              <li key={i} data-i={i} ref={(el) => { refs.current[i] = el; }} className={active === i ? "on" : ""}>
                <span className="lp-stepnum">{i + 1}</span>
                <h3>{s.title}</h3>
                <p>{s.text}</p>
                <div className="lp-step-vis">{vis[i]}</div>
              </li>
            ))}
          </ol>
          <div className="lp-sticky" aria-hidden="true">
            <div className="lp-panel">
              {vis.map((v, i) => <div key={i} className={"lp-pane" + (active === i ? " on" : "")}>{v}</div>)}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ---------- funzioni ---------- */
const GLYPH = ["♛", "♞", "♜", "♝", "♚", "♙"];
function Features({ c }: { c: Copy }) {
  return (
    <section id="features" className="lp-section">
      <div className="lp-wrap">
        <h2 className="lp-h2 narrow">{c.features.title}</h2>
        <div className="lp-bento">
          {c.features.items.map((f, i) => (
            <article key={i} className={"lp-feat f" + i} onMouseMove={spot}>
              <span className="lp-glyph" aria-hidden="true">{GLYPH[i]}</span>
              <h3>{f.title}</h3>
              <p>{f.text}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------- prova interattiva ---------- */
function Demo({ c }: { c: Copy }) {
  const [sel, setSel] = useState(0);
  const [n, setN] = useState(0);
  const it = c.demo.items[sel];
  const parts = [it.error, it.idea, it.rule];
  const total = parts.join("").length;
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setN(total); return; }
    setN(0);
    const t = setInterval(() => setN((x) => (x >= total ? x : x + 2)), 16);
    return () => clearInterval(t);
  }, [sel, total, c]);
  let off = 0;
  return (
    <section className="lp-section lp-demo-sec">
      <div className="lp-wrap lp-demo">
        <div>
          <h2 className="lp-h2">{c.demo.title}</h2>
          <p className="lp-sub">{c.demo.sub}</p>
          <div className="lp-picks" role="tablist">
            {c.demo.items.map((x, i) => (
              <button key={i} role="tab" aria-selected={sel === i} className={sel === i ? "on" : ""} onClick={() => setSel(i)}>{x.label}</button>
            ))}
          </div>
        </div>
        <div className="lp-lesson" aria-live="polite">
          <span className="lp-tag">{c.demo.example}</span>
          {parts.map((p, i) => {
            const shown = p.slice(0, Math.max(0, Math.min(p.length, n - off)));
            off += p.length;
            return <div key={i} className="lp-lblock"><b>{c.demo.heads[i]}</b><p>{shown}{shown.length < p.length && shown.length > 0 && <span className="caret" />}</p></div>;
          })}
        </div>
      </div>
    </section>
  );
}

/* ---------- prezzi ---------- */
const PLANS: { k: "Free" | "Plus" | "Pro" | "Elite"; price: string }[] = [
  { k: "Free", price: "0" }, { k: "Plus", price: "3,99" }, { k: "Pro", price: "6,99" }, { k: "Elite", price: "12,99" },
];
function Pricing({ c, lang }: { c: Copy; lang: string }) {
  return (
    <section id="pricing" className="lp-section">
      <div className="lp-wrap">
        <h2 className="lp-h2">{c.pricing.title}</h2>
        <p className="lp-sub">{c.pricing.sub}</p>
        <div className="lp-plans">
          {PLANS.map((p) => (
            <article key={p.k} className={"lp-plan" + (p.k === "Pro" ? " hot" : "")} onMouseMove={spot}>
              {p.k === "Pro" && <span className="lp-badge">{c.pricing.popular}</span>}
              <h3>{p.k}</h3>
              <p className="lp-blurb">{c.pricing.plans[p.k].blurb}</p>
              <div className="lp-price">€{lang === "en" ? p.price.replace(",", ".") : p.price}<small>{c.pricing.month}</small></div>
              <ul>{c.pricing.plans[p.k].items.map((x) => <li key={x}>{x}</li>)}</ul>
              <Link href={SIGNUP} className={"btn btn-lg " + (p.k === "Pro" ? "btn-primary" : "btn-ghost")}>{c.pricing.start} {p.k}</Link>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function Faq({ c }: { c: Copy }) {
  return (
    <section id="faq" className="lp-section">
      <div className="lp-wrap lp-faq">
        <h2 className="lp-h2">{c.faq.title}</h2>
        <div>
          {c.faq.items.map((f) => (
            <details key={f.q}><summary>{f.q}</summary><p>{f.a}</p></details>
          ))}
        </div>
      </div>
    </section>
  );
}

function Final({ c }: { c: Copy }) {
  return (
    <section className="lp-final">
      <div className="lp-wrap">
        <span className="lp-bigglyph" aria-hidden="true">♞</span>
        <h2>{c.final.title}</h2>
        <p className="lp-lead">{c.final.sub}</p>
        <Link href={SIGNUP} className="btn btn-primary btn-lg">{c.final.cta}</Link>
      </div>
    </section>
  );
}

function Footer({ c }: { c: Copy }) {
  return (
    <footer className="lp-footer">
      <div className="lp-wrap lp-foot-in">
        <div><Logo size={30} /><p>{c.footer.text}</p></div>
        <div className="lp-foot-r"><span className="lp-foot-links"><Link href="/privacy">Privacy</Link><Link href="/terms">{c.footer.terms}</Link></span><a href={`mailto:${SUPPORT}`}>{c.footer.support}: {SUPPORT}</a><span>© {new Date().getFullYear()} {BRAND}</span></div>
      </div>
    </footer>
  );
}

export default function Landing() {
  const { lang } = useLang();
  const c = COPY[lang];
  return (
    <div className="lp">
      <div className="lp-grain" aria-hidden="true" />
      <Nav c={c} />
      <main>
        <Hero c={c} />
        <Marquee c={c} />
        <How c={c} />
        <Features c={c} />
        <Demo c={c} />
        <Pricing c={c} lang={lang} />
        <Faq c={c} />
        <Final c={c} />
      </main>
      <Footer c={c} />
    </div>
  );
}
