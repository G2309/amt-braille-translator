"""Parser MusicXML -> AST 

Implementacion minima con xml.etree, soporta:
- partwise MusicXML 
- dos pentagramas de piano (staff 1 = mano derecha, staff 2 = mano izquierda)
- notas, silencios, acordes (<chord/>), puntillos, alteraciones
- armadura (<fifths>) e indicacion de compas (<time>)

Fuera de alcance v0: in-accords (voces), ligaduras, repeticiones.
"""
import xml.etree.ElementTree as ET
from typing import Optional

from .model import Chord, Measure, Note, Rest, Score


def _octave_musicxml_to_braille(octave_xml: int) -> int:
    """MusicXML usa octavas cientificas (C4 = Do central); el Manual numera
    las octavas Braille del 1 al 7 con la 4a como central. Coinciden para
    el rango util del piano, con recorte a los extremos 1..7."""
    return max(1, min(7, octave_xml))


def parse_musicxml(path: str) -> Score:
    tree = ET.parse(path)
    root = tree.getroot()

    score = Score()

    title_el = root.find(".//work/work-title")
    if title_el is not None and title_el.text:
        score.title = title_el.text.strip()

    part = root.find("part")
    if part is None:
        raise ValueError("MusicXML sin elemento <part>")

    for m_el in part.findall("measure"):
        m_num = int(m_el.get("number", "0"))
        rh_measure = Measure(m_num)
        lh_measure = Measure(m_num)

        attributes = m_el.find("attributes")
        if attributes is not None:
            fifths = attributes.find("key/fifths")
            if fifths is not None:
                score.fifths = int(fifths.text)
            time = attributes.find("time")
            if time is not None:
                score.beats = int(time.find("beats").text)
                score.beat_type = int(time.find("beat-type").text)

        pending_chord: Optional[Chord] = None
        pending_staff = 1

        def flush_chord():
            nonlocal pending_chord
            if pending_chord is not None:
                target = rh_measure if pending_staff == 1 else lh_measure
                if len(pending_chord.notes) == 1:
                    single = pending_chord.notes[0]
                    single.duration_type = pending_chord.duration_type
                    single.dots = pending_chord.dots
                    target.events.append(single)
                else:
                    target.events.append(pending_chord)
                pending_chord = None

        for n_el in m_el.findall("note"):
            staff_el = n_el.find("staff")
            staff = int(staff_el.text) if staff_el is not None else 1

            dtype_el = n_el.find("type")
            dtype = dtype_el.text if dtype_el is not None else "quarter"
            n_dots = len(n_el.findall("dot"))

            if n_el.find("rest") is not None:
                flush_chord()
                pending_staff = staff
                target = rh_measure if staff == 1 else lh_measure
                target.events.append(Rest(dtype, n_dots))
                continue

            pitch = n_el.find("pitch")
            step = pitch.find("step").text
            octave = _octave_musicxml_to_braille(int(pitch.find("octave").text))
            alter_el = pitch.find("alter")
            alter = int(alter_el.text) if alter_el is not None else 0
            explicit = n_el.find("accidental") is not None

            note = Note(
                step=step,
                octave=octave,
                duration_type=dtype,
                alter=alter,
                dots=n_dots,
                explicit_accidental=explicit,
            )

            is_chord_member = n_el.find("chord") is not None
            if is_chord_member and pending_chord is not None and staff == pending_staff:
                pending_chord.notes.append(note)
            else:
                flush_chord()
                pending_staff = staff
                pending_chord = Chord(notes=[note], duration_type=dtype, dots=n_dots)

        flush_chord()
        score.right.measures.append(rh_measure)
        score.left.measures.append(lh_measure)

    return score
