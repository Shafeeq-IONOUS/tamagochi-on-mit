; =============================================================================
;  The building's mind.
;
;  These are the actual rules that decide what the building does. They are not
;  a configuration file being read by Python -- they are a program, in MeTTa,
;  a language built for reasoning with symbols rather than crunching numbers.
;
;  Everything else in this project is arithmetic: waves, chemistry, growth,
;  colour. This is the one part that reasons. It never touches a pixel and it
;  runs twice a second, nowhere near the drawing loop.
;
;  HOW TO READ A RULE
;
;    (= (decide just-now high $c $f $k) (20 startle))
;
;  "When contact was JUST NOW and arousal is HIGH -- whatever the curiosity,
;   fatigue and crowd happen to be -- express STARTLE, at rank 20."
;
;  Anything beginning with $ is a blank: it matches anything.
;
;  WHY EVERY RULE CARRIES A RANK
;
;  More than one rule can match the same situation, so something has to decide
;  which wins. The obvious answer -- whichever is written first -- turns out to
;  be wrong: MeTTa returns every match it finds and does not promise them in
;  the order they appear in the file. Relying on that quietly produced a
;  DIFFERENT answer from the same rules in 66 of 324 possible situations,
;  depending on which engine was running.
;
;  So precedence is written down instead of implied. Lowest rank wins, both
;  engines sort the same way, and you can see the priority order by reading the
;  numbers rather than by knowing how the interpreter happens to search.
;
;  The five inputs, in order:
;    contact    just-now | recent | a-while | alone
;    arousal    low | mid | high      how activated it is
;    curiosity  low | mid | high      how much it wants something to happen
;    fatigue    low | mid | high      builds with activity, clears with rest
;    crowd      none | some | many    people per minute lately
; =============================================================================


; --- Somebody is touching it right now ---------------------------------------
; The crowd rule is habituation, and it is the most important line here. A body
; stops flinching at something that keeps happening -- the thirtieth person in a
; minute is not a shock. Without it the building flinched over and over all
; through a crowd, which reads as broken rather than alive.
(= (decide just-now $a   $c $f many)   (10 memory))
(= (decide just-now high $c $f $k)     (20 startle))
(= (decide just-now $a   $c $f $k)     (30 attention))


; --- Somebody was here in the last half minute -------------------------------
; A crowd that has just been through has GROWN something. Show them what they
; built rather than a record of where they stood: it is the same information
; and it is a far better thing to look at.
(= (decide recent $a   $c   $f many)   (40 tree))
(= (decide recent $a   high $f $k)     (50 attention))
(= (decide recent high $c   $f $k)     (60 seismic))
(= (decide recent $a   $c   $f $k)     (70 attention))


; --- The last contact is fading ----------------------------------------------
; Tired means it stops performing and starts dwelling on what happened.
(= (decide a-while $a $c   high $k)    (80 dream))
(= (decide a-while $a $c   $f   many)  (90 tree))
(= (decide a-while $a high $f   $k)    (100 memory))
(= (decide a-while $a $c   $f   $k)    (110 reef))
(= (decide a-while $a $c   $f   $k)    (215 forecast))


; --- Nobody has been near for a long time ------------------------------------
; Left completely alone it does not switch off. Tired, it dreams. Restless, it
; sweeps the sky with the radar on its own roof. Otherwise it watches the
; weather, which is what this building was built to do.
(= (decide alone $a   $c   high $k)    (120 dream))
(= (decide alone $a   high $f   $k)    (130 radar))
(= (decide alone high $c   $f   $k)    (140 aurora))
; Left alone, the useful thing is the default. A landmark that spends its quiet
; hours telling the city what the weather is doing is an instrument; one that
; spends them looking pretty is decoration. This ranks above the weather modes
; deliberately -- being useful should not have to compete for attention.
(= (decide alone $a   $c   $f   $k)    (145 forecast))
(= (decide alone $a   $c   $f   $k)    (150 sounding))


; --- Room to learn -----------------------------------------------------------
; When nobody is near, ANY of the weather worlds is appropriate. These rules do
; not change what the building does on its own -- the ranked answers above still
; win outright -- they widen what the LEARNER is allowed to pick from.
;
; This matters because being alone is most of the night, and it is exactly when
; the building most needs to find out what draws somebody in. With one permitted
; answer there is nothing to learn from; with five there is.
(= (decide alone   $a $c $f $k)        (160 aurora))
(= (decide alone   $a $c $f $k)        (170 radar))
(= (decide alone   $a $c $f $k)        (180 reef))
(= (decide alone   $a $c $f $k)        (190 tree))
(= (decide a-while $a $c $f $k)        (200 tree))
(= (decide a-while $a $c $f $k)        (210 aurora))


; --- Last resort --------------------------------------------------------------
; If somehow nothing above matched, watch the weather. Never leave the building
; with no instruction.
(= (decide $w $a $c $f $k)             (999 sounding))
