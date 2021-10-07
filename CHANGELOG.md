# Change Log

This document records the main changes to the `opscore` code.

## 3.0.4 (2021-10-07)

### 🔧 Fixed

* Decode the reply string before parsing it into keywords. This actually enables keyword parsing which was broken.


## 3.0.3 (2021-08-17)

### 🔧 Fixed

* Fix more internal `RO` imports.
* `TCPSocket` end of line changed to `\r\n` (as unicode).


## 3.0.2

* Never tagged.


## 3.0.1 (2021-08-12)

### 🔧 Fixed

* Fix internal `RO` imports.
* Use bytes for EOF delimiters in Twisted subclasses.


## 3.0.0 (2021-08-12)

### Support

* Refactored to work with Python 3 (only).
* Implemented proper packaging.


## v2_5 (2017-06-11)

### Added

* Ticket #1421: Keyword parser does not accept extra values. Needs version v4_1 of actorcore.
* Ticket #1217: A few desired enhancements to Keywords and Keyword. Keyword is now easier to get items from and loop over. Keywords has a new ``get`` method.
