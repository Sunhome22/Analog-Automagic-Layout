### Things to implement/fix
- Traces:
  - [x] Make traces half the width longer in desired direction :check: 
  - [x] NAME instead of id number on trace name
- Linear Optimization:
  - [x]Bulk connection logic is not entirely correct
- Connections:
  - [x] Some functionality was lost, and now it generates too many connections. Fixed
- UNIT TEST
- ASTAR
  - [x] Updates Astar, such that when connecting from areas that have local connections the two closes ports are chosen.
  - [] Introduce constraints for how close each path is
  - [] VSS in locali and VDD in m1



- req:
  - contourpy==1.3.1
cycler==0.12.1
fonttools==4.55.3
kiwisolver==1.4.8
matplotlib==3.10.0
numpy==2.1.1
packaging==24.2
pillow==10.4.0
PuLP==2.9.0
pyparsing==3.2.1
python-dateutil==2.9.0.post0
six==1.17.0
