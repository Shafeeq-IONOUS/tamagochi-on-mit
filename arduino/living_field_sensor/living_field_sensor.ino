/*
  Living Field -- the building's sense of touch.
  For the Arduino Uno R4 WiFi.

  This board has one job: shout two numbers down the USB cable, thirty times a
  second. The laptop does all the thinking.

      SHADOW,KNOCK,VOLUME,BRIGHT
      1023,0,243,293   <- no light sensor, no piezo, two knobs
      1023,0,800,293   <- somebody turned the volume up
      1023,0,800,980   <- and the brightness up

  With no light sensor wired, SHADOW is always 1023 -- "nothing is blocking
  the light" -- and KNOCK is always 0. The laptop reads that as nobody being
  there, which is exactly right, and takes its touches from the phone page
  instead.

  SHADOW is how much light is falling on the sensor. Bright room = a big number.
  Put your hand over it and the number drops. That is the building noticing you.

  KNOCK is 1 for one single reading when the piezo disc is tapped, otherwise 0.

  VOLUME and BRIGHT are the two knobs, 0 to 1023.

    VOLUME  turns the music up and down. The laptop passes it to Spotify.
            The board is a CONTROLLER, not a player: Spotify streams are
            DRM-protected and need OAuth, TLS and a codec, and this board has
            thirty-two kilobytes of memory and no audio output. There is
            nothing to port and no point trying.

    BRIGHT  dims the building. Worth having a physical one, because you can
            hand somebody the knob, let them turn it all the way up, and show
            them it still cannot pass the safety ceiling. That is a better
            argument than a paragraph about it.

  ---------------------------------------------------------------------------
  AND IT LISTENS BACK
  ---------------------------------------------------------------------------

  The laptop sends the tree back down the same cable, once every tenth of a
  second, as one line of 96 digits:

      M:000110000000011100000000...

  Each digit is one of the 96 LEDs on this board, and the board just draws it.
  So the little grid in your hand shows the SAME TREE the tower is showing --
  the crowd's branches, growing in your palm while they grow twenty-one storeys
  up. Holding the two next to each other is the best thirty seconds of the
  demo, and it costs one line of code on each side.

  If nothing is sent, the grid falls back to showing the sensor reading, so the
  board is still useful on its own.

  ---------------------------------------------------------------------------
  WIRING -- about five minutes, no soldering
  ---------------------------------------------------------------------------

  Light sensor (the little orange disc, either way round):
      one leg  -> 5V
      other leg -> A0  AND  through a 10k resistor -> GND

    The resistor is what turns "how much light" into a voltage the board can
    read. Without it you just read noise.

  Knock sensor (the small round black disc with a red and a black wire):
      black wire -> GND
      red wire   -> A1  AND  through a 1M resistor -> GND

  Two knobs (potentiometers, three legs each):
      left leg  -> GND
      right leg -> 5V
      middle leg -> A2 on the first knob, A3 on the second

    The middle leg is the wiper: it reports where the knob is pointing, as a
    voltage somewhere between the two outer legs. Which way round the outer
    legs go only decides which way is "up".

    This part is normally a buzzer. Tapping it makes a tiny bit of electricity,
    so it works backwards as a knock detector. The big resistor drains that
    charge away so it is ready for the next knock.

  If you have no parts wired up at all, this still runs and prints steady
  numbers. Nothing breaks.
*/

#include "Arduino_LED_Matrix.h"

ArduinoLEDMatrix matrix;

// ---------------------------------------------------------------------------
//  WHAT IS ACTUALLY WIRED
//
//  Right now: two knobs, on A0 and A1. Nothing else.
//
//  Set a pin to -1 and that input is simply not there. The laptop treats every
//  input as optional, so a half-built rig works exactly as well as a finished
//  one -- it just does less.
// ---------------------------------------------------------------------------
const int VOLUME_PIN = A0;    // knob one  -> music volume
const int BRIGHT_PIN = A1;    // knob two  -> dims the building

// Nothing is wired to the light sensor or the piezo, so those two channels
// are simply reported as "nothing there" rather than read from a pin.
//
// Written as plain constants instead of a pin of -1 and a clever guard. The
// guarded version compiled and uploaded happily and then the board went silent
// -- analogRead(-1) still sat in the binary. Not worth the cleverness.
const int NO_LIGHT = 1023;    // 1023 = nothing blocking the light
const int NO_KNOCK = 0;

// Potentiometers jitter by a count or two constantly. Smoothing them here
// costs nothing and stops the laptop firing a volume change thirty times a
// second over noise that nobody asked for.
int volSmooth = 512;
int brtSmooth = 900;

// How hard a tap has to be before it counts. Raise it if the sensor is jumpy,
// lower it if gentle taps are being missed.
const int KNOCK_THRESHOLD = 60;

// After a knock, ignore the pin briefly. One physical tap rings the disc
// several times, and without this you get five knocks from one finger.
const unsigned long KNOCK_COOLDOWN_MS = 220;

unsigned long lastKnockAt = 0;

// The board's own little 12x8 grid: a miniature of the tower.
uint8_t frame[8][12];

// Set true once the laptop starts sending pictures, so we stop drawing the
// fallback and show the real thing instead.
bool receiving = false;
unsigned long lastFrameAt = 0;
const unsigned long FRAME_TIMEOUT_MS = 1500;

char inbuf[110];
int inlen = 0;

void setup() {
  Serial.begin(115200);
  matrix.begin();
  // Deliberately NOT waiting for a serial connection here. `while (!Serial);`
  // is the usual line and it would mean the board does nothing at all until a
  // laptop opens the port -- including not driving its own LED grid.
}

void loop() {
  // 1023 means "plenty of light, nothing blocking it", which is what the
  // laptop should believe when there is no light sensor at all.
  int shadow = NO_LIGHT;
  int tap    = NO_KNOCK;

  // A slow average: mostly the old value, a little of the new one.
  volSmooth = (volSmooth * 7 + analogRead(VOLUME_PIN)) / 8;
  brtSmooth = (brtSmooth * 7 + analogRead(BRIGHT_PIN)) / 8;

  int knock = 0;
  unsigned long now = millis();
  if (tap > KNOCK_THRESHOLD && (now - lastKnockAt) > KNOCK_COOLDOWN_MS) {
    knock = 1;
    lastKnockAt = now;
  }

  // Only speak when somebody is listening, and only when there is room.
  //
  // This is the difference between a board that works and a board that dies
  // silently ten minutes into a demo.
  //
  // Serial here is USB CDC. When the laptop closes the port the board carries
  // on printing into a buffer nobody is draining, and once that buffer is full
  // Serial.print BLOCKS -- forever. The sketch stops, the little grid freezes,
  // and the board stays dead until it is physically unplugged. It looks exactly
  // like a flashing problem and it is not.
  //
  //   if (Serial)   is a host actually connected?
  //
  // That one test is enough: with no host there is nothing to fill, so nothing
  // to block on, and the moment something reconnects it starts talking again.
  //
  // The first attempt also required availableForWrite() > 32. That looked more
  // careful and made the board completely silent -- this core's CDC does not
  // report free space the way the check assumed. A safety check that silences
  // the thing it is protecting is worse than no check.
  if (Serial) {
    Serial.print(shadow);
    Serial.print(",");
    Serial.print(knock);
    Serial.print(",");
    Serial.print(volSmooth);
    Serial.print(",");
    Serial.println(brtSmooth);
  }

  readFromLaptop();

  if (receiving && (millis() - lastFrameAt) < FRAME_TIMEOUT_MS) {
    matrix.renderBitmap(frame, 8, 12);     // the tree, as sent
  } else {
    receiving = false;
    drawMiniTower(shadow, knock);          // no laptop: show the sensor
  }

  delay(33);   // about thirty times a second, same as the building
}

/*
  Read a picture of the tower, if the laptop has sent one.

  The format is deliberately the dumbest thing that works: the letter M, a
  colon, then 96 characters of 0 or 1, then a newline. No lengths, no checksum,
  nothing to get out of step -- a line either arrives whole or it is ignored,
  and a dropped line just means this frame looks like the last one.
*/
void readFromLaptop() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      if (inlen > 97 && inbuf[0] == 'M' && inbuf[1] == ':') {
        for (int i = 0; i < 96; i++) {
          frame[i / 12][i % 12] = (inbuf[i + 2] == '1') ? 1 : 0;
        }
        receiving = true;
        lastFrameAt = millis();
      }
      inlen = 0;
    } else if (inlen < (int)sizeof(inbuf) - 1) {
      inbuf[inlen++] = c;
    }
  }
}

/*
  A tiny version of the building, in your hand.

  The darker it is over the sensor, the higher the light climbs up the little
  grid -- so when you cover the sensor, this fills up at the same moment the
  real tower leans towards you. Holding this next to the real building while it
  responds is the best thirty seconds of the demo, and it costs nothing.
*/
void drawMiniTower(int shadow, int knock) {
  // With no light sensor there is no shadow to show, so the little grid
  // follows the brightness knob -- something in your hand that moves when you
  // turn it.
  int covered = map(constrain(brtSmooth, 0, 1023), 0, 1023, 0, 8);
  for (int row = 0; row < 8; row++) {
    for (int col = 0; col < 12; col++) {
      bool lit = (8 - row) <= covered;     // fills from the bottom upward
      frame[row][col] = (knock || lit) ? 1 : 0;
    }
  }
  matrix.renderBitmap(frame, 8, 12);
}
