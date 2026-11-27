%% Numeric APMCM H5 style. Order: first citation, without sorting.
%% Journals: Author. Title[J]. Journal. Year. Volume. Pages/article number.
%% Books: Author. Title[M]. Place: Publisher. Year. Cited pages.
%% Online: Author. Title. URL. Accessed date (mandatory).
ENTRY
 { address author doi editor eid journal note pages publisher title
   url urldate volume year }
 {} {}
INTEGERS { nameptr namesleft numnames }
STRINGS { s t }
FUNCTION {format.names}
{ 's := #1 'nameptr := s num.names$ 'numnames :=
  numnames 'namesleft :=
  { namesleft #0 > }
  { s nameptr "{vv~}{ll}{, f.}{, jj}" format.name$ 't :=
    nameptr #1 >
      { namesleft #1 > { ", " * t * } { " and " * t * } if$ }
      { t }
    if$
    nameptr #1 + 'nameptr := namesleft #1 - 'namesleft :=
  } while$
}
FUNCTION {authors}
{ author empty$
  { editor empty$
    { "Missing author/editor in " cite$ * warning$ "[Author pending]" }
    { editor format.names " (ed.)" * } if$ }
  { author format.names } if$
}
FUNCTION {required.title}
{ title empty$
  { "Missing title in " cite$ * warning$ "[Title pending]" }
  { title } if$ write$
}
FUNCTION {required.year}
{ year empty$
  { "Missing year in " cite$ * warning$ "[Year pending]" }
  { year } if$ write$
}
FUNCTION {output.bibitem}
{ newline$ "\bibitem{" write$ cite$ write$ "}" write$ newline$
  authors add.period$ write$ " " write$
}
FUNCTION {finish.entry}
{ doi empty$ 'skip$
  { " DOI: \href{https://doi.org/" write$ doi write$ "}{" write$
    doi write$ "}." write$ } if$
  note empty$ 'skip$
  { " \emph{" write$ note write$ ".}" write$ } if$
  newline$
}
FUNCTION {article}
{ output.bibitem required.title "[J]. " write$
  journal empty$
  { "Missing journal in " cite$ * warning$ "[Journal pending]" }
  { journal } if$ write$ ". " write$ required.year ". " write$
  volume empty$
  { "Missing volume in " cite$ * warning$ "[Volume pending]" }
  { volume } if$ write$ ". " write$
  pages empty$
  { eid empty$
    { "Missing pages/eid in " cite$ * warning$ "[Pages pending]" }
    { "Article " eid * } if$ }
  { pages } if$ write$ "." write$ finish.entry
}
FUNCTION {book}
{ output.bibitem required.title "[M]. " write$
  address empty$ 'skip$ { address write$ ": " write$ } if$
  publisher empty$
  { "Missing publisher in " cite$ * warning$ "[Publisher pending]" }
  { publisher } if$ write$ ". " write$ required.year ". " write$
  pages empty$
  { "Missing cited page range in " cite$ * warning$ "[Pages pending]" }
  { pages } if$ write$ "." write$ finish.entry
}
FUNCTION {online}
{ output.bibitem required.title ". " write$
  url empty$
  { "Missing URL in " cite$ * warning$ "[URL pending]" write$ }
  { "\url{" write$ url write$ "}" write$ } if$
  ". Accessed " write$
  urldate empty$
  { "Missing access date in " cite$ * warning$ "[Access date pending]" }
  { urldate } if$ write$ "." write$ finish.entry
}
FUNCTION {misc} { online }
FUNCTION {default.type} { online }
FUNCTION {begin.bib}
{ "\begin{thebibliography}{99}" write$ newline$ }
FUNCTION {end.bib}
{ newline$ "\end{thebibliography}" write$ newline$ }
READ
EXECUTE {begin.bib}
ITERATE {call.type$}
EXECUTE {end.bib}
