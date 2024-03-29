#!/usr/bin/env python

"""A window (Tk Toplevel widget) for setting preferences.

To Do:
- If window is closed without saving changes, ask user to save changes.
- Hot help and a status line for errors and general info
- Set list width based on contents
- Only include a scrollbar if more than 10? elements (could be user-settable)
  and shorten the list to fit if fewer than that number (it grows anyway)

History:
2002-02-01 R Owen: begun coding
2002-02-06 R Owen: still need to connect up the command buttons Cancel, Use and Save.
    Not hard to do -- just loop through the pref editors and call the appropriate method!
2002-02-07 R Owen: implemented file I/O and connected up all the buttons
2002-02-08 R Owen: added color prefVars to the test code
2002-03-01 R Owen: removed header for each panel and overhauled the controls to match new pref editor controls.
2002-03-08 R Owen: modified test code to demonstrate auto update of widgets by ColorPrefVar and FontPrefVar.
2003-04-09 ROwen    Changed shortDescr to helpText, preperatory to full help implementation.
2003-04-21 ROwen    Renamed StatusWdg to StatusBar to avoid conflicts.
2003-06-18 ROwen    Modified to test for StandardError instead of Exception
2003-10-14 ROwen    Modified applyPrefs to only apply changed prefs.
                    This greatly speeds up applying and saving prefs
                    at a small cost in increased risk.
2003-10-16 ROwen    Output messages to status bar, not stderr.
2004-05-18 ROwen    Stopped importing sys since it was not being used.
2005-01-05 ROwen    Changed level to severity; modified to use opscore.RO.Constants.
2005-08-12 ROwen    Removed unused import of string module.
2005-09-15 ROwen    Added getCategories and showCategory methods.
                    Renamed internal method selectCategory to _showSelectedCategory.
2012-07-10 ROwen    Removed use of update_idletasks.
2012-12-19 ROwen    Added a FontSizePrefVar to the demo.
2014-08-31 ROwen    Added a contextual menu with Help (if helpURL provided) to all controls;
                    formerly only the status bar had this.
2015-11-03 ROwen    Replace "!= None" with "is not None" to modernize the code.
"""
__all__ = ["PrefWin", "PrefWdg"]

from six.moves import tkinter
from . import PrefVar
from . import PrefEditor
import opscore.RO.Constants
import opscore.RO.Wdg

class PrefWin(opscore.RO.Wdg.Toplevel):
    def __init__(self,
        master,
        prefSet,
        title = "Preferences",
        *args,
        **kwargs
    ):
        opscore.RO.Wdg.Toplevel.__init__(self, master, title=title, *args, **kwargs)
        self.prefWdg = PrefWdg(self, prefSet)
        self.prefWdg.pack(fill=tkinter.BOTH, expand=tkinter.YES)


class PrefWdg(tkinter.Frame):
    """Frame for editing preferences."""

    def __init__(self,
        master,
        prefSet,
        helpURL = None,
    ):
        self.prefSet = prefSet
        tkinter.Frame.__init__(self, master)

        self.prefsByCat = self.prefSet.getCategoryDict()
        catList = self.getCategories()

        # create the list of categories
        catListFrame = tkinter.Frame(self)
        catListScroll = tkinter.Scrollbar(catListFrame, orient="vertical")
        self.catListWdg = tkinter.Listbox(
            catListFrame,
            selectmode="browse",
            yscrollcommand = catListScroll.set,
        )
        self.catListWdg.insert(0, *catList)
        catListScroll.configure(command=self.catListWdg.yview)
        self.catListWdg.grid(row=0, column=0, sticky="nsew")
        catListScroll.grid(row=0, column=1, sticky="ns")
        catListFrame.grid(row=0, column=0, sticky="nsew")
        catListFrame.grid_rowconfigure(0, weight=1)

        # create the status widget
        self.statusBar = opscore.RO.Wdg.StatusBar(
            master = self,
            helpURL = helpURL,
        )
        self.statusBar.grid(row=1, column=0, columnspan=2, sticky="ew")

        # create the button panel
        self.buttonWdg = tkinter.Frame(self)
        buttonList = (
            self._getShowMenu(self.buttonWdg, helpURL=helpURL),
            tkinter.Frame(self.buttonWdg, width=10),
            opscore.RO.Wdg.Button(self.buttonWdg, text="Apply", command=self.applyPrefs, helpURL=helpURL),
            opscore.RO.Wdg.Button(self.buttonWdg, text="Save", command=self.writeToFile, helpURL=helpURL),
        )
        for button in buttonList:
            button.pack(side="left")
        self.buttonWdg.grid(row=2, column=0, columnspan=2, sticky="nsew")
        buttonList[0].helpText = "Restore all displayed values to the specified state"
        buttonList[2].helpText = "Apply changes (making them current) but do not save"
        buttonList[3].helpText = "Apply changes and save them to a file"


        # create a frame for displaying the preferences for a given category
        self.editFrame = tkinter.Frame(self, relief="ridge", border=1)
        self.editFrame.grid(row=0, column=1, sticky="nsew")
        # pack a tiny frame so it shrinks to fit
        tkinter.Frame(self.editFrame, height=0, width=0).pack()
        # self.editFrame.grid_rowconfigure(0, weight=1)
        # self.editFrame.grid_columnconfigure(0, weight=1)
        self.paneDict = {}
        self.prefEditorList = []
        for cat, prefs in self.prefsByCat.items():
            prefFrame = tkinter.Frame(self.editFrame)
            self.paneDict[cat] = prefFrame
            row = 0
            column = 0
            for pref in prefs:
                prefEditor = PrefEditor.getPrefEditor(
                    prefVar = pref,
                    master = prefFrame,
                    row = row,
                    column = column,
                )
                self.prefEditorList.append(prefEditor)
                row += 1
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # set up category list binding and select first category
        self.currCat = None
        self.catListWdg.bind("<ButtonRelease>", self._showSelectedCategory)
        if catList:
            self.showCategory(catList[0])

    def _showSelectedCategory(self, evt=None):
        """Queries the prefs category list for the currently chosen category
        and displays the proper prefs panel. Called automatically when the user
        clicks on a category.
        """
        indexList = self.catListWdg.curselection()
        if not indexList:
            # nothing selected, so nothing done
            return
        cat = self.catListWdg.get(indexList[0])

        if cat == self.currCat:
            # no change in selected; nothing done
            return

        if self.currCat is not None:
            self.paneDict[self.currCat].pack_forget()
        self.paneDict[cat].pack(fill="both")
        self.currCat = cat

    def applyPrefs(self, evt=None):
        """Apply all unapplied changes"""
        self.statusBar.setMsg(
            msgStr = "Applying prefs",
        )
        for prefEditor in self.prefEditorList:
            if prefEditor.unappliedChanges():
                prefEditor.setVariable()
        self.statusBar.setMsg(
            msgStr = "Prefs applied",
        )

    def getCategories(self):
        """Return a list of preference categories"""
        return list(self.prefsByCat.keys())

    def showCategory(self, catName):
        """Show the specified category.
        Raise ValueError if not found.
        """
        catList = self.getCategories()
        catInd = catList.index(catName)
        self.catListWdg.selection_clear(0)
        self.catListWdg.selection_set(catInd)
        self._showSelectedCategory()

    def showCurrentValue(self, evt=None):
        """Resets all preference editors to the current value of the preference"""
        for prefEditor in self.prefEditorList:
            prefEditor.showCurrentValue()

    def showInitialValue(self, evt=None):
        """Resets all preference editors to the initial value of the preference"""
        for prefEditor in self.prefEditorList:
            prefEditor.showInitialValue()

    def showDefaultValue(self, evt=None):
        """Sets all preference editors to their default value"""
        for prefEditor in self.prefEditorList:
            prefEditor.showDefaultValue()

    def writeToFile(self, evt=None):
        """Updates all preferences and saves the results"""
        self.applyPrefs()
        try:
            self.prefSet.writeToFile()
        except Exception as e:
            self.statusBar.setMsg(
                msgStr = "Save failed: %s" % (e,),
                severity = opscore.RO.Constants.sevError,
            )
        else:
            self.statusBar.setMsg(
                msgStr = "Prefs saved to %s" % (self.prefSet.defFileName,),
                severity = opscore.RO.Constants.sevNormal,
            )

    def unappliedChanges(self):
        """Returns true if the user has made changes that have not been applied"""
        result = 0
        for prefEditor in self.prefEditorList:
            if prefEditor.unappliedChanges():
                result = 1
                break
        return result

    def _getShowMenu(self, master, helpURL=None):
        mbut = tkinter.Menubutton(master,
            indicatoron=1,
            direction="below",
            borderwidth=2,
            relief="raised",
            highlightthickness=2,
            text="Show",
        )
        opscore.RO.Wdg.addCtxMenu(mbut, helpURL=helpURL)
        mnu = tkinter.Menu(mbut, tearoff=0)
        mnu.add_command(label="Current", command=self.showCurrentValue)
        mnu.add_command(label="Initial", command=self.showInitialValue)
        mnu.add_command(label="Default", command=self.showDefaultValue)
        mbut["menu"] = mnu
        return mbut


if __name__ == "__main__":
    from opscore.RO.Wdg.PythonTk import PythonTk
    root = PythonTk()

    defMainWdg = tkinter.Label()
    entryWdg = tkinter.Entry()
    menuWdg = tkinter.Menu()

    pvList = (
        PrefVar.FontPrefVar(
            name = "Main Font",
            category = "fonts",
            defWdg = defMainWdg,
            optionPatterns = ("*font",),
            helpText = "font for labels, menus, etc.",
        ),
        PrefVar.FontSizePrefVar(
            name = "Entry Font",
            category = "fonts",
            defWdg = entryWdg,
            optionPatterns = ("*Entry.font",),
            helpText = "font for entry widgets",
        ),
        PrefVar.FontSizePrefVar(
            name = "Menu Font",
            category = "fonts",
            defWdg = menuWdg,
            optionPatterns = ("*Menu.font",),
            helpText = "font for menu items",
        ),
        PrefVar.ColorPrefVar(
            name = "Background Color",
            category = "colors",
            defValue = tkinter.Label().cget("background"),
            wdgOption = "background",
            helpText = "background color for most widgets",
        ),
        PrefVar.ColorPrefVar(
            name = "Foreground Color",
            category = "colors",
            defValue = tkinter.Label().cget("foreground"),
            wdgOption = "foreground",
            helpText = "foreground color for most widgets",
        ),
        PrefVar.ColorPrefVar(
            name = "Invalid Background",
            category = "colors",
            defValue = "red",
            helpText = "background color for invalid data",
        ),
        PrefVar.StrPrefVar(
            name = "String1",
            category = "strings",
            defValue = "",
            helpText = "string with no restrictions",
        ),
        PrefVar.StrPrefVar(
            name = "String2",
            category = "strings",
            defValue = "foo",
            partialPattern = r"^[a-z]*$",
            helpText = "string with format ^[a-z]*$",
        ),
        PrefVar.StrPrefVar(
            name = "String3",
            category = "strings",
            defValue = "foo",
            validValues = ("foo", "bar", "baz"),
            partialPattern = r"^[a-z]*$",
            helpText = "multiple choice string",
        ),
        PrefVar.IntPrefVar(
            name ="Int1",
            category = "ints",
            defValue = 0,
            helpText = "int with no restrictions",
        ),
        PrefVar.IntPrefVar(
            name = "Int2",
            category = "ints",
            defValue = 45,
            maxValue = 99,
            helpText = "int with default 45 and upper limit 99",
        ),
        PrefVar.IntPrefVar(
            name = "Int3",
            category = "ints",
            defValue = 0,
            minValue = -75,
            helpText = "int with lower limit of -75",
        ),
        PrefVar.IntPrefVar(
            name = "Int4",
            category = "ints",
            defValue = 4,
            minValue = -9,
            maxValue =  9,
            helpText = "int with range of [-9, 9]",
        ),
        PrefVar.IntPrefVar(
            name = "Int4",
            category = "ints",
            defValue = 4,
            validValues = list(range(8, -10, -2)),
            minValue = -9,
            maxValue =  9,
            helpText = "int with range of [-9, 9]",
        ),
        PrefVar.BoolPrefVar(
            name = "Bool1",
            category = "bools",
            defValue = True,
            helpText = "boolean with default = True",
        ),
        PrefVar.BoolPrefVar(
            name = "Bool2",
            category = "bools",
            defValue = False,
            helpText = "boolean with default = False",
        ),
        PrefVar.FloatPrefVar(
            name = "Float1",
            category = "floats",
            defValue = 0,
            helpText = "float with no restrictions",
        ),
        PrefVar.FloatPrefVar(
            name = "Float2",
            category = "floats",
            defValue = 0,
            maxValue = 99.99,
            helpText = "float with upper limit of 99.99",
        ),
        PrefVar.FloatPrefVar(
            name = "Float3",
            category = "floats",
            defValue = 0,
            minValue = -75.50,
            helpText = "float with lower limit of -75.50",
        ),
        PrefVar.FloatPrefVar(
            name = "Float4",
            category = "floats",
            defValue = 0,
            minValue = -9.99,
            maxValue =  9.99,
            helpText = "float with range of [-9.99, 9.99]",
        ),
        PrefVar.DirectoryPrefVar(
            name = "Dir1",
            category = "files",
            helpText = "existing directory",
        ),
        PrefVar.FilePrefVar(
            name = "File1",
            category = "files",
            helpText = "existing file",
        ),
        PrefVar.SoundPrefVar(
            name = "Sound1",
            category = "sounds",
            helpText = "sound file",
            bellNum = 1,
        ),
        PrefVar.SoundPrefVar(
            name = "Sound2",
            category = "sounds",
            helpText = "sound file",
            bellNum = 2,
            bellDelay = 50,
        ),
    )

    prefSet = PrefVar.PrefSet(
        prefList = pvList,
        defFileName = "PWPrefs.txt",
        defHeader = """Test preferences for PrefWdg.py\n"""
    )
    try:
        prefSet.readFromFile()
    except Exception as e:
        print("could not read prefs:", e)

    testFrame = PrefWdg (root, prefSet = prefSet)
    testFrame.pack(fill=tkinter.BOTH, expand=tkinter.YES)

    testFrame.showCategory("colors")

    root.mainloop()
