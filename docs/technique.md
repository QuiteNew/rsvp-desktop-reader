# The science behind RSVP

RSVP Desktop Reader shows one word at a time in a fixed spot, with a single
letter highlighted. The idea is simple to use and surprisingly deep underneath,
resting on decades of research into how the eye moves, where it lands, and what
actually limits reading speed. This page walks through that background: how
ordinary reading works, what the highlighted letter is really doing, where the
one-word-at-a-time method came from, and what studies have found about whether
it helps. The short version is that the technique is clever and genuinely
useful for some things, and also not the dramatic speed boost it has sometimes
been sold as.

## How the eye reads

Reading feels continuous, as though the eye slides evenly along each line. It
does not. The eye moves in quick jumps, called saccades, with brief pauses
between them, called fixations. Reading happens only during the pauses. During
a jump the image on the retina smears across the visual field too fast to use,
and the brain suppresses it, so for those few tens of milliseconds you are
effectively blind and simply do not notice.

Decades of eye-tracking have made the pattern precise. A skilled adult reading
silently fixates for about 200 to 250 milliseconds at a time, then jumps
forward roughly 7 to 9 letters, a distance of about two degrees of visual angle
(Rayner, 2009). Somewhere between one jump in seven and one in ten goes
backward instead of forward. Those backward jumps, called regressions, make up
about 10 to 15% of all saccades, and they turn out to matter more than they
look.

The jumping exists because sharp vision is scarce. Only a tiny central region
of the retina, the fovea, sees in high detail, and it covers around two degrees
of the visual field, a patch barely wide enough for a handful of letters at
normal reading distance. Everything outside it gets blurrier fast. To read a
whole line, the eye has no choice but to keep moving that small sharp window
along the text, word by word.

How much you actually pick up around each fixation is called the perceptual
span, and it was mapped in the 1970s with an elegant trick: a moving-window
display that shows normal text only within a few characters of where the reader
is looking and replaces the rest with other letters (McConkie & Rayner, 1975).
By shrinking and growing that window and watching when reading slows down, you
can measure the span directly. For English it is asymmetric: a reader takes in
detail about 3 to 4 characters to the left of fixation and 14 to 15 to the
right, biased toward the text still to come.

That rightward reach is not wasted. The blurry preview of the next word or two,
known as parafoveal preview, lets the brain begin working on a word before the
eye ever lands on it, which is part of why fluent reading feels so effortless.
A single-word display gives none of that. Each word arrives on its own, with no
run-up and nothing waiting in the wings.

## Why one letter is highlighted

The highlighted letter comes from a narrower finding: when the eye fixates a
word, how fast and how accurately you recognize it depends on where in the word
the eye lands.

Two threads of research describe this. The first is where the eyes naturally
tend to land, which is not the first letter but a point between the start and
the middle of the word, the preferred viewing location (Rayner, 1979). The
second is where recognition is actually best, which is slightly left of the
word's center. Land there and the word is identified fastest and with the
fewest errors; land at either edge and performance falls off, more steeply
toward the end than the start. That sweet spot is the optimal viewing position,
established by O'Regan, Jacobs and colleagues across the 1980s and early 1990s
(O'Regan & Jacobs, 1992). The reason is geometric. From just left of center,
the whole word sits inside or close to the sharp foveal region. Fixate the
first letter of a long word and its ending trails off into the blur; fixate the
end and the beginning is already gone.

The one-word readers took this idea and built an interface around it. Spritz,
the app that brought the approach to a wide audience in 2014, named the letter
near that position the Optimal Recognition Point, colored it red, and aligned
every word so that letter always falls on the same spot (van der Hoop, 2014).
With the words registered to a fixed point, the eye never has to hunt for where
to look, and in principle it can spend its time recognizing rather than aiming.
RSVP Desktop Reader works the same way, computing each word's recognition-point
letter, highlighting it, and holding it at one horizontal position so the eye
can settle in a single place.

One caveat is worth keeping straight. "Optimal Recognition Point" is an app-era
name; the underlying science, the optimal viewing position, is about where the
eye chooses to fixate inside a word. A single-word display removes that choice
entirely, since there is only ever one word and the eye is not scanning a line.
So the highlight is best understood as a visual anchor that keeps one word
landing where the last one did, rather than a literal re-creation of the
viewing-position effect. Useful, but for a slightly different reason than the
marketing implies.

## Where RSVP came from

Rapid serial visual presentation is far older than any reading app. It started
as a method for studying perception and attention in the lab. In the late 1960s
and 1970s, Mary C. Potter and Ellen Levy flashed rapid sequences of pictures to
measure how quickly the mind takes in a scene (Potter & Levy, 1969), and
Kenneth Forster presented word sequences the same way to study how sentences
are understood (Forster, 1970). Showing stimuli one at a time, in one place, at
a controlled rate gave researchers precise command over exactly what reached the
eye and when, which made RSVP a natural experimental tool long before anyone
thought of it as a way to get through email.

It became a mainstay of cognitive psychology. It is the standard way to study
the attentional blink, the curious fact that when two targets appear in quick
succession in a fast stream, people frequently miss the second (Raymond,
Shapiro & Arnell, 1992). It has also shown how fast meaning can register at all:
viewers can catch the gist of a picture shown for as little as 13 milliseconds
(Potter, Wyble, Hagmann & McCourt, 2014). Findings like that are part of what
makes the single-word reading idea so tempting. If the visual system can grab a
word in a flash, the thinking goes, why not simply deliver words as fast as it
can take them?

RSVP has one setting where its value for reading is well supported: low vision.
People with central-field loss have to read using peripheral vision, where eye
movements and visual crowding are especially punishing. Presenting words one at
a time in a fixed location removes the hardest part of that, and training
studies in this population report real gains in reading rate (building on work
such as Pelli and colleagues, 2007).

## Does it make you read faster?

For ordinary readers, the evidence is more sobering, and it is worth looking at
directly.

The selling point rests on a single premise: that moving the eyes is what costs
you, so removing the movement removes the bottleneck. Spritz framed eye movement
as roughly 80% of conventional reading time (van der Hoop, 2014). The trouble is
that the mechanics do not support it. The jumps themselves are brief, a few tens
of milliseconds each, while the fixations where reading actually happens run
five to ten times longer. Very little of reading time is literally spent in
motion. What takes the time is processing, and the ceiling on how much you can
absorb per fixation is set by language and comprehension, not by how quickly the
eye can be moved. A 2016 review of the whole field stated it plainly: the limit
is cognitive and linguistic, and the fuzziness of peripheral vision is a feature
of how the system allocates its limited sharp vision, not an obstacle an
interface can design away (Rayner, Schotter, Masson, Potter & Treiman, 2016).

Taking eye movement away also removes two things that were doing real work. The
first is rereading. Regressions are not a bad habit; they are repair. A study
tracked readers' eyes and masked each word the instant the eye moved past it, so
that looking back revealed nothing. Comprehension dropped, for plain and
ambiguous sentences alike, and the authors concluded that the freedom to look
back is part of understanding, not a detour around it (Schotter, Tran & Rayner,
2014). A one-word stream makes that impossible by construction; the word is
simply gone. The second is the parafoveal preview described earlier, the quiet
head start on the next word, which a single-word display cannot provide.

Push the rate up and the costs grow. Comprehension slips and visual fatigue
climbs as words come faster, and studies of trained speed readers have long
found the same tradeoff: the faster they read, the less they retain (Rayner et
al., 2016). A typical adult reads for comprehension at somewhere around 200 to
300 words per minute. Driving a one-word reader to 600 or 1,000 is less reading
faster than skimming with the gaps politely hidden. There is no setting at which
full comprehension and several-times-normal speed hold at once.

## What it is actually good for

The honest case for the technique is narrower than the pitch, and more
interesting for being true.

It does remove the search for where to look next, and whatever that is worth,
for some readers on some material a single fixed point is simply more
comfortable than scanning. It is a strong pacing and focus aid: a steady,
externally set rhythm leaves little room to drift off, trail away, or drift back
over the same line without noticing, and for getting through lighter or familiar
material, or for staying on task when attention is thin, that structure can be
the entire benefit. It asks almost nothing of the screen, which suits phones and
small displays, and it has the genuine low-vision uses noted above.

It also rewards matching the method to the material. Straightforward prose you
want to move through briskly is a good fit. Dense, technical, or closely argued
text, the kind where a reader naturally slows down, pauses, and looks back, is
exactly where losing the ability to regress costs the most. The useful habit is
to settle on the fastest speed at which you still genuinely follow the meaning,
rather than the highest number you can endure, and to ease off for anything that
deserves it.

## How this app applies it

RSVP Desktop Reader leans on what the technique does well and deliberately
softens its sharpest limitation. The fixed reading point and the highlighted
letter handle the anchoring side. The pacing is not flatly uniform: words that
close a sentence or a clause are held a little longer, which leaves a beat to
absorb meaning before the next one arrives, and an optional ease-in opens a
session more slowly so the eyes settle before reaching full speed.

The part the research is clearest about is the freedom to go back, and the app
keeps it rather than throwing it away. You can pause, skip backward, drag the
progress bar to any earlier word, and leave bookmarks to return to a spot later.
Classic RSVP removes regressions as a matter of design; here they come back as
deliberate controls you reach for when you want them. The aim is not to outrun
the way reading works, which does not go well, but to work alongside it, treating
the single-word display as a focus and pacing tool rather than a promise of
impossible speed.

## Sources and further reading

If you want to go past my summary, here's where it all traces back, roughly in
order of how useful it is to actually read.

Start with the two that are written for normal humans and are free online:

- Rayner, Schotter, Masson, Potter & Treiman (2016), *So Much to Read, So Little
  Time*. This is the one to read if you read only one. A whole team of the
  field's heavyweights sat down specifically to answer "can speed reading
  work," and the short answer is "not the way the apps claim." Overview here:
  https://www.psychologicalscience.org/publications/speed_reading.html
- Schotter, Tran & Rayner (2014), *Don't Believe What You Read (Only Once)*.
  This is the "regressions actually matter" experiment, and it name-checks the
  one-word apps directly. Readable writeup:
  https://today.ucsd.edu/story/dont_believe_what_you_read_only_once_speed_reading_apps_may_impair_reading

The numbers about how the eye moves (the 200 to 250 ms fixations, the 7 to 9
letter jumps, the 10 to 15% regressions, the lopsided perceptual span) all come
from Keith Rayner, who basically spent a career on this. A good dense summary is
Rayner (2009), *Eye movements and attention in reading*:
https://pages.ucsd.edu/~bkbergen/cogs200/Rayner-Bartlett.pdf

For background on what RSVP even is and where it's used, the Wikipedia page is a
fine starting point:
https://en.wikipedia.org/wiki/Rapid_serial_visual_presentation

And if you want to see where the "Optimal Recognition Point" marketing came
from, this is roughly the moment Spritz showed up in 2014 claiming 1,000 words a
minute:
https://thewritelife.com/new-speed-reading-app-spritz/

Then there are the classic papers behind specific claims. These are mostly
paywalled or library-only, but they're easy to find by title if you want the
primary source:

- McConkie & Rayner (1975), the moving-window trick that first measured how wide
  the "useful" window around your eye actually is.
- Rayner (1979), on where the eye tends to land inside a word (not the first
  letter).
- O'Regan & Jacobs (1992), the optimal-viewing-position work, i.e. the real
  science the highlighted letter is loosely based on.
- Potter & Levy (1969) and Forster (1970), the early lab experiments that
  basically invented RSVP before anyone thought to read with it.
- Raymond, Shapiro & Arnell (1992), the "attentional blink," which is the thing
  RSVP is most famous for in psychology.
- Potter et al. (2014), the one showing you can get the gist of a picture in
  about 13 milliseconds, which is the kind of result that makes fast reading
  sound more plausible than it is.
