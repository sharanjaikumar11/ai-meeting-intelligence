# Meeting dataset preparation

The user selected public English meeting recordings. The initial dataset is a three-meeting subset of the AMI Meeting Corpus. Actual recordings and references are stored under `C:\Users\shara\Projects\ai-meeting-intelligence\data`; this repository contains the manifest and preparation code.

| Meeting | Project split | Audio minutes | Speakers | Lexical words |
| --- | --- | ---: | ---: | ---: |
| ES2002a | Development | 21.21 | 4 | 2600 |
| ES2003a | Validation | 19.00 | 4 | 2038 |
| ES2004a | Held-out test | 17.49 | 4 | 2614 |

Total: 57.70 minutes, 7,252 lexical words, 610 transcript segments. These are project subset assignments, not the full official AMI benchmark. Participants are corpus speaker labels A-D, not inferred real-world identities.

Source: AMI Consortium / University of Edinburgh, [official download page](https://groups.inf.ed.ac.uk/ami/download/). Audio and manual annotations v1.6.2 are provided under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Download URLs and SHA-256 checksums are retained in `data/provenance.json` in the environment directory. Derived JSON and text are mechanical conversions of the corpus annotations; they have not been newly transcribed or independently human-reviewed by us.

Preparation checks that every included lexical word belongs to exactly one reference segment and timestamps remain within the recording. Punctuation-only and non-speech XML nodes are omitted. Original summary sections are retained without converting them into inferred structured owners or deadlines.

Day 1 model comparison uses three fixed 60-second windows from ES2002a, starting at 60, 600, and 900 seconds. An initial 1080-1140 second window was rejected because it extended beyond manual transcript coverage, although the recording continued. All models are compared again on the corrected common set (benchmark version 2). ES2004a is not used for model selection. These clips are not sufficient for the Day 9 evaluation report.

Annotation requirements to complete alongside the relevant later modules:
- A verbatim reference transcript for WER.
- Speaker labels and names only where established.
- Summary and key discussion points.
- Action items, assigned persons, deadlines, and pending questions.
- Initial decisions, proposed changes, accepted changes, final decisions, disagreements, and unresolved discussions.
- QA reference answers for tasks by person, pending tasks, decisions, and final deadlines, with supporting transcript passages.

The initial subset supplies speech, overlaps, role assignments, and corpus action/decision summaries. Explicit deadline revisions and unresolved-decision histories still need targeted coverage review; do not assume every required scenario occurs in these recordings. Keep development and evaluation meetings separate. Unknown dates, people, and task status must remain unknown.

Do not label the most recently mentioned proposal as the final decision without evidence of agreement. Task status is as of the recording, not the present day.

Record the meeting date/timezone when known so relative deadlines can be interpreted. Do not invent these values.
