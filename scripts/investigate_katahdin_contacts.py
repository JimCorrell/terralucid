#!/usr/bin/env python3
"""Bounded two-contact shell/two-hole interpretation; not a general repair."""
import math
from collections import Counter
from shapely.geometry import Polygon,LinearRing
from investigate_county_zoning_cases import interpret
from investigate_osborn_zoning import edges

def split_two_contacts(ring):
    if len(ring)<10 or ring[0]!=ring[-1] or any(len(p)!=2 or not all(math.isfinite(v) for v in p) for p in ring):
        raise ValueError('Expected finite closed 2D ring')
    if any(a==b for a,b in zip(ring,ring[1:])):raise ValueError('Consecutive duplicate vertex')
    counts=Counter(map(tuple,ring[:-1]));repeated={p:n for p,n in counts.items() if n>1}
    if len(repeated)!=2 or set(repeated.values())!={2}:raise ValueError('Expected exactly two twice-visited vertices')
    # Recursively cut at the first repeated coordinate by slicing the original
    # traversal, distinct from the reviewer's stack-based source cycle walk.
    pending=[ring];loops=[]
    while pending:
        r=pending.pop();positions={};cut=None
        for j,p in enumerate(r[:-1]):
            key=tuple(p)
            if key in positions:cut=(positions[key],j);break
            positions[key]=j
        if cut:
            a,b=cut;pending.extend([r[a:b+1],r[b:]+r[1:a+1]])
        else:loops.append(r)
    if len(loops)!=3 or any(len(r)<4 or not Polygon(r).is_valid or Polygon(r).area<=0 for r in loops):raise ValueError('Expected three simple nondegenerate cycles')
    shells=[r for r in loops if not LinearRing(r).is_ccw];holes=[r for r in loops if LinearRing(r).is_ccw]
    if len(shells)!=1 or len(holes)!=2:raise ValueError('Expected one clockwise shell and two counterclockwise holes')
    s=Polygon(shells[0]);hp=[Polygon(r) for r in holes]
    if any(not s.covers(h) for h in hp) or hp[0].intersection(hp[1]).area!=0:raise ValueError('Holes are not contained and interior-disjoint')
    candidate=Polygon(shells[0],holes)
    if not candidate.is_valid:raise ValueError('Unsupported contacts after separation')
    if edges([ring])!=edges(loops):raise ValueError('Changed segment multiplicity')
    return loops,{'type':'two_contacts_shell_two_holes','repeated_vertices':sorted(map(list,repeated)),'source_coordinate_count':len(ring),'cycle_coordinate_counts':[len(r) for r in loops],'cycle_area_m2':[Polygon(r).area for r in loops],'cycle_counterclockwise':[LinearRing(r).is_ccw for r in loops],'segments_preserved_with_multiplicity':True}

def propose_katahdin(rings):
    invalid=[i for i,r in enumerate(rings) if not Polygon(r).is_valid]
    if invalid!=[0]:raise ValueError('Expected only source ring zero to be invalid')
    loops,diagnostic=split_two_contacts(rings[0]);g,assembly=interpret(loops+rings[1:])
    output=[list(p.exterior.coords) for p in g.geoms]+[list(h.coords) for p in g.geoms for h in p.interiors]
    if edges(rings)!=edges(output):raise ValueError('Changed complete-source segments')
    return g,{'splits':[dict(diagnostic,source_ring=0)],'assembly':assembly}

def review_katahdin_cycles(rings,candidate):
    """Review fixed geometry using the separate stack walk and signed cycles."""
    from review_moosehead_spencer import walk_cycles,signature
    if not candidate.is_valid or candidate.is_empty or candidate.geom_type!='MultiPolygon':raise ValueError('Invalid candidate')
    all_cycles=[walk_cycles(r) for r in rings]
    if [i for i,c in enumerate(all_cycles) if len(c)>1]!=[0] or len(all_cycles[0])!=3:raise ValueError('Unexpected source cycle structure')
    first=all_cycles[0];shell=[c for c in first if not LinearRing(c).is_ccw];holes=[c for c in first if LinearRing(c).is_ccw]
    if len(shell)!=1 or len(holes)!=2:raise ValueError('Unexpected source cycle roles')
    owner=[i for i,p in enumerate(candidate.geoms) if signature(p.exterior.coords)==signature(shell[0])]
    if len(owner)!=1:raise ValueError('Missing original shell')
    retained={signature(h.coords) for h in candidate.geoms[owner[0]].interiors}
    if any(signature(h) not in retained for h in holes):raise ValueError('Two holes must retain their source shell')
    shells=[c for cc in all_cycles for c in cc if not LinearRing(c).is_ccw];all_holes=[c for cc in all_cycles for c in cc if LinearRing(c).is_ccw]
    if Counter(signature(c) for c in shells)!=Counter(signature(p.exterior.coords) for p in candidate.geoms):raise ValueError('Changed shell cycles')
    if Counter(signature(c) for c in all_holes)!=Counter(signature(h.coords) for p in candidate.geoms for h in p.interiors):raise ValueError('Changed hole cycles')
    return {'source_cycle_roles_preserved':True,'exact_shell_cycles':len(shells),'exact_hole_cycles':len(all_holes),'split_rings':[{'source_ring':0,'cycles':3,'type':'shell_two_holes','candidate_shell_index':owner[0],'loop_area_m2':[Polygon(c).area for c in first],'counterclockwise':[LinearRing(c).is_ccw for c in first]}]}
