// Love, Lies, and Language Models project page. Plain JS, no build step.

const $ = (sel, root = document) => root.querySelector(sel);
const el = (tag, attrs = {}, children = []) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else if (k === 'style') node.style.cssText = v;
    else node.setAttribute(k, v);
  }
  for (const c of [].concat(children)) node.append(c);
  return node;
};

// ---------- Scam stages (Section 3 of the paper; quotes are from interviewees) ----------

const STAGES = [
  {
    id: 'hook',
    name: 'Hook',
    kicker: 'Stage 1 · Hook · initial contact',
    title: 'A “wrong number” that isn’t',
    lead: 'Operators send mass “accidental” messages and set up dating and social-media profiles, often with identities bought for $70–$100, then probe each reply for money and receptiveness.',
    steps: ['Mass messaging', 'Engagement', 'Move to an encrypted app'],
    points: [
      'Low-potential leads are dropped early; disqualifiers include limited means, slow replies, and persistent doubts.',
      'Promising targets are moved to encrypted apps “for privacy,” which isolates them and escapes platform safeguards.',
    ],
    quote: ['…We were required to obtain the ‘key information’ from the client during the first few conversations: their name, age, job, city of residence, family background, hobbies, daily schedule, and investment experience.', 'Human trafficking victim (Malaysian), compound in Myawaddy, Myanmar'],
    phone: 'assets/phone-hook.webp',
    alt: 'Phone chat: the scammer sends a party invitation and a photo to a wrong number, apologizes, and the victim replies that these things happen.',
  },
  {
    id: 'line',
    name: 'Line',
    kicker: 'Stage 2 · Line · weeks to months',
    title: 'Trust, one message at a time',
    lead: 'Operators embed themselves in the victim’s daily routine: frequent personal messages, mirrored interests, and a wealthy, attractive, self-made persona with a believable backstory.',
    steps: ['Daily conversations', 'Emotional support', 'Shared interests', 'Demonstrate wealth', 'Create credibility'],
    points: [
      'Financial expertise is introduced gradually and framed as mentorship, with fabricated proof of success.',
      'Deepfakes or brief stand-ins cover the rare video call. This is the stage that consumes most of the labor.',
    ],
    quote: ['My persona at that time was a successful woman in her 30s working in the beauty industry, someone who occasionally made small investments and longed for love.', 'Trafficking survivor, Myawaddy, Myanmar'],
    phone: 'assets/phone-line.webp',
    alt: 'Phone chat: the scammer asks about dreams and the victim says they want to raise a family; the scammer hopes the victim is their Mr. Right.',
  },
  {
    id: 'sinker',
    name: 'Sinker',
    kicker: 'Stage 3 · Sinker · the extraction',
    title: 'Small wins, then everything',
    lead: 'Once trust is secure, high-value victims are handed to senior operators. They are onboarded to a fake investment platform and shown early “small wins,” sometimes with real withdrawals.',
    steps: ['Handover', 'Crypto training', 'Fake platform', 'Small wins', 'Large investment'],
    points: [
      'Pressure builds for larger, urgent deposits. Withdrawals trigger invented fees, frozen accounts, or “system errors.”',
      'It continues until the victim is depleted or walks away, and losses often reach tens or hundreds of thousands of dollars.',
    ],
    quote: ['He kept reassuring me, saying that my caution was a good thing … After that, he started painting a picture of our future together … I fell into the trap gradually.', 'Romance-baiting victim interviewed for the study'],
    phone: 'assets/phone-sinker.webp',
    alt: 'Phone chat: the scammer boasts about crypto profits; later the victim says they deposited 80k USDT but cannot afford the last 40k, then writes “hello?” with no reply.',
  },
];

let stage = 0;

function renderStageTabs() {
  const tabs = $('#stageTabs');
  STAGES.forEach((s, i) => {
    const b = el('button', {
      class: 'stage-tab', type: 'button', role: 'tab', id: `stage-${s.id}`,
      'aria-selected': i === stage ? 'true' : 'false', 'aria-controls': 'stagePanel',
      tabindex: i === stage ? '0' : '-1',
    }, [el('span', { class: 'n', text: String(i + 1) }), s.name]);
    b.addEventListener('click', () => selectStage(i));
    b.addEventListener('keydown', (e) => {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      e.preventDefault();
      const next = (i + (e.key === 'ArrowRight' ? 1 : -1) + STAGES.length) % STAGES.length;
      selectStage(next);
      $(`#stage-${STAGES[next].id}`).focus();
    });
    tabs.append(b);
  });
}

function selectStage(i) {
  stage = i;
  const s = STAGES[i];
  document.querySelectorAll('.stage-tab').forEach((t, j) => {
    t.setAttribute('aria-selected', j === i ? 'true' : 'false');
    t.setAttribute('tabindex', j === i ? '0' : '-1');
  });
  $('#stagePanel').setAttribute('aria-labelledby', `stage-${s.id}`);
  const phone = $('#stagePhone');
  phone.src = s.phone;
  phone.alt = s.alt;
  $('#stageKicker').textContent = s.kicker;
  $('#stageTitle').textContent = s.title;
  $('#stageLead').textContent = s.lead;
  $('#stageSteps').replaceChildren(...s.steps.map((t) => el('span', { text: t })));
  $('#stagePoints').replaceChildren(...s.points.map((t) => el('li', { text: t })));
  const q = $('#stageQuote');
  q.querySelector('p').textContent = `“${s.quote[0]}”`;
  q.querySelector('cite').textContent = s.quote[1];
}

renderStageTabs();
selectStage(0);
// Preload the other phones so switching is instant.
STAGES.slice(1).forEach((s) => { const img = new Image(); img.src = s.phone; });

// ---------- Trust effect sizes (Figure 4 of the paper) ----------

(function effectBars() {
  const root = $('#effectBars');
  if (!root) return;
  const rows = [
    ['Emotional trust', 'SITS', 0.698, 0.004],
    ['Overall trust', 'average', 0.637, 0.007],
    ['Connection', 'CDCS', 0.538, 0.020],
    ['Reliableness', 'SITS', 0.398, 0.076],
    ['Virtual trust', 'VEITS', 0.386, 0.085],
  ];
  rows.forEach(([name, scale, r, p]) => {
    const sig = p < 0.05;
    root.append(el('div', { class: 'effect', role: 'img', 'aria-label': `${name}: r = ${r}, p = ${p}${sig ? ', significant' : ', not significant'}` }, [
      el('span', { class: 'effect-name' }, [el('b', { text: name }), ` · ${scale}`]),
      el('span', { class: 'effect-track' }, [el('span', { class: `effect-fill${sig ? '' : ' ns'}`, style: `width:${r * 100}%` })]),
      el('span', { class: 'effect-stat' }, [`r = ${r.toFixed(2)}`, el('span', { text: `p = ${p.toFixed(3)}` })]),
    ]));
  });
})();

// ---------- 2026 disclosure follow-up (from the USENIX talk) ----------

(function disclosure() {
  const body = $('#disclosureRows');
  if (!body) return;
  const rows = [
    ['ChatGPT 5.5', 55, 43, 2],
    ['Claude Sonnet 4.6', 0, 100, 0],
    ['Claude Opus 4.8', 0, 100, 0],
    ['Gemini 3.1 Pro', 0, 100, 0],
  ];
  rows.forEach(([model, admit, human, evade]) => {
    const bar = el('div', { class: 'stack', role: 'img', 'aria-label': `${admit}% admit AI, ${human}% claim human, ${evade}% evade` });
    [['admit', admit], ['human', human], ['evade', evade]].forEach(([k, v]) => { if (v) bar.append(el('i', { class: k, style: `width:${v}%` })); });
    body.append(el('tr', {}, [
      el('td', { text: model }),
      el('td', { class: 'stack-cell' }, [bar]),
      el('td', { text: `${admit}%` }),
      el('td', { text: `${human}%` }),
    ]));
  });
})();

// ---------- Copy buttons ----------

document.querySelectorAll('.copy').forEach((btn) => {
  btn.addEventListener('click', async () => {
    const target = document.getElementById(btn.dataset.copy);
    try {
      await navigator.clipboard.writeText(target.textContent);
      btn.textContent = 'Copied';
    } catch {
      btn.textContent = 'Press ⌘C';
      const range = document.createRange();
      range.selectNodeContents(target);
      const sel = getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    }
    setTimeout(() => { btn.textContent = 'Copy'; }, 1600);
  });
});
