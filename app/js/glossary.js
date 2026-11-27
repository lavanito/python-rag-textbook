// Glossary links in the page text (A5; decision 2a, 27 November 2026).
//
// The first use of each glossary term in each section of the page is linked
// to its definition (hover, focus or tap). This file finds the uses in one
// piece of text; the page applies it to the text of each section.
//
// Rules:
// - each term has its link forms (data/glossary.csv): its preferred label
//   and the alternative labels in use on the page; a plural in -s or -es
//   counts as the same form;
// - at any place in the text, the longest form found is taken, so
//   "Governed RAG" is one use of Governed RAG, not a use of RAG;
// - a form written with capitals inside it or with no small letters
//   ("DQR", "BM25", "ABox") must match exactly; any other form matches in
//   any case ("Edition" and "edition");
// - a form is matched only as whole words: "PPP" is not found inside "PPPs-based";
// - a term already linked in the section (`seen`) is not linked again.

(function () {
  function escapeRegExp(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function exactCase(form) {
    return !/[a-z]/.test(form) || /^\S+$/.test(form) && /.[A-Z]/.test(form);
  }

  // terms: [{id, link_forms: [...]}] -> a matcher for linkText.
  function compile(terms) {
    const forms = [];
    for (const t of terms) for (const f of t.link_forms) forms.push({ form: f, id: t.id, exact: exactCase(f) });
    forms.sort((a, b) => b.form.length - a.form.length || (a.form < b.form ? -1 : 1));
    const byLower = new Map();
    for (const f of forms) {
      const key = f.form.toLowerCase();
      if (!byLower.has(key)) byLower.set(key, []);
      byLower.get(key).push(f);
    }
    const pattern = forms.map((f) => escapeRegExp(f.form)).join("|");
    return { byLower, regex: pattern ? new RegExp(`(?<![\\w-])(${pattern})(?:e?s)?(?![\\w-])`, "gi") : null };
  }

  // The text in parts: [{text}] for plain text, [{text, id}] for a linked use.
  function linkText(text, matcher, seen) {
    const parts = [];
    if (!matcher.regex) return [{ text }];
    let last = 0;
    matcher.regex.lastIndex = 0;
    let m;
    while ((m = matcher.regex.exec(text)) !== null) {
      const candidates = matcher.byLower.get(m[1].toLowerCase()) || [];
      const hit = candidates.find((f) => !f.exact || f.form === m[1]);
      if (!hit || seen.has(hit.id)) continue;
      seen.add(hit.id);
      if (m.index > last) parts.push({ text: text.slice(last, m.index) });
      parts.push({ text: m[0], id: hit.id });
      last = m.index + m[0].length;
    }
    if (last < text.length) parts.push({ text: text.slice(last) });
    return parts;
  }

  globalThis.glossaryCode = { compile, linkText, exactCase };
})();
