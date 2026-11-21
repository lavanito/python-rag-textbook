# Knowledge graph (ontology and triplets)

A small, hand-built knowledge graph of the ideas in the corpus and how they
relate. Chapter 5 uses it to widen searches (a query for "volume measure" also
finds "constant prices" and "chain-linked") and to move between manuals (from
a BEA passage to the equivalent SNA or ESA paragraph). Chapter 12 uses the
question types and indicators to split a vague question.

## Terms

- **Ontology:** the rules. It lists which kinds of thing exist and which
  relations may link them. Here: `schema.json`.
- **Knowledge graph:** an ontology together with the facts that follow its
  rules: the things, and the triplets that link them. Here: all three files.
- **Concept map:** a diagram of concepts joined by labelled arrows, with no
  fixed rules on kinds or relations. This folder is not one: every fact must
  pass the ontology's rules, and a test checks that it does.

| File | What it holds |
| --- | --- |
| `schema.json` | The ontology: six kinds of thing and twelve relations, each with the kind of its subject and object |
| `entities.csv` | Every thing in the graph: id, kind, label, and other names (aliases) separated by semicolons |
| `triples.csv` | Triplets as subject, relation, object, with the evidence for each: a passage id, or `author` for the author's own framing |

Each line of `triples.csv` is one triplet, for example
`terms_of_trade, defined_in, sna08-15.187`.

Which manual each passage comes from is not repeated here: it is the
`source_code` field of each passage in `data/corpus/passages.jsonl`, and the
code reads it from there.

`tests/test_knowledge_graph.py` checks that every triplet uses a declared
relation, that subject and object have the kinds the relation requires, that
every passage id exists, and that every triplet has evidence.

## Known gaps

- Only the economies whose manual is certain are linked to one (United States:
  BEA; euro area: ESA 2010).

## Extracted triplets (Chapter 13)

Chapter 13 has the local model read each passage and propose triplets in the
same three-part form. The code compares them with this hand-built graph and
reports how many are right, wrong or missing; doubtful ones go to the author
to check. The hand-built graph is the answer key.

## Where a larger system would differ

This graph has 67 things and 131 triplets, typed in by hand and read by plain
Python. A commercial system with millions of series would store the same kind
of facts in a graph database such as Neo4j, or as RDF with an OWL ontology,
extract many of them from documents with a language model and have people
check the doubtful ones, and search them with a search engine such as
Elasticsearch or OpenSearch. The ideas are the same: kinds of thing, typed
relations, evidence for each fact. Appendix D loads this graph into Neo4j.

## Measures (indicators), added 16 November 2026

The horizontal domain expert decided on 16 November 2026 that the graph holds the
catalogue of measures, so a question can be read against things and triplets
rather than matched to a whole banked question.

- Every measure of the NNI model (`ragbook/ch13_model_tool.py`, `MEASURES`)
  is an `Indicator`, with other names a reader might type. Two ids differ from
  the measure's name because a concept already uses that id:
  `population_total` (measure `population`) and `gni_total` (measure `gni`).
- `gni_per_hour_ppp` is a measure the NNI model does not have; the nearest is
  `real_nni_per_hour`.
- `real_gdp` was renamed `real_gdp_growth`, and `real_gdp_per_hour_ppp` was
  renamed `gdp_per_hour`, to match the NNI model.
- `defined_in` and `discussed_in` now allow an `Indicator` as subject. A
  measure is `defined_in` a passage only when the passage defines the whole
  measure: GNI total, population and average hours. The other measures are
  built from parts, so every passage in their definition line
  (`data/definitions.csv`) is `discussed_in`: their definition line is
  assembled from passages (the horizontal domain expert, 16 November 2026).
- `requires` links each question type to the measures that answer it;
  `affected_by` links measures to known measurement problems.

## Controlled vocabulary, first set (added 21 November 2026)

`controlled_vocabulary.csv` is the governed list of terms: the first layer of
Governed RAG's knowledge graph, kept apart from the book glossary. The first
set is the 13 NNI model measures, the six economies and Ireland, and the
eight input flags (28 terms).

- One row per term. Columns follow the import format of Talisman's SKOS
  editor (`id`, `prefLabel`, `altLabel`, `hiddenLabel`, `definition`,
  `scopeNote`, `notation`, `broader`, `related`, `exactMatch`; several values
  separated by " | "), then ours: `scheme`, `series`, `definitionSource`,
  `writtenBy`, `checkedBy`, `status`, `created`, `modified`.
- Roles (21 November 2026): the vertical domain expert writes each
  definition; the horizontal domain expert checks it against the vocabulary
  rules and maintains it. Status is `approved` or `draft`. The 13 measure
  definitions are the lines approved on 13 November (`data/definitions.csv`);
  the economy and flag definitions are drafts.
- Concept, series and figure are kept apart: a measure is a concept; the
  series codes it is calculated from are in `series`; figures stay in the data.
- Aliases are written only here. `tools/sync_vocabulary_aliases.py` copies
  the alternative labels into the aliases of `entities.csv`;
  `tests/test_vocabulary.py` fails if the two differ.
- Not yet: `broader`, `related` and `exactMatch` (taxonomy, thesaurus and
  authority links) wait for gate C8a.
