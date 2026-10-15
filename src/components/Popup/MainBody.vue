<template>
  <div
    id="codes"
    v-bind:class="{ filter: shouldFilter && filter, search: showSearch }"
  >
    <!-- Filter -->
    <div class="under-header" id="filter" v-on:click="clearFilter()">
      {{ i18n.show_all_entries }}
    </div>
    <!-- Search -->
    <div class="under-header" id="search">
      <input
        id="searchInput"
        v-model="searchText"
        v-bind:placeholder="i18n.search"
        type="text"
        tabindex="-1"
      />
      <div id="searchHint" v-if="searchText === ''">
        <div></div>
        <div id="searchHintBorder">/</div>
        <div></div>
      </div>
    </div>
    <!-- Folders -->
    <div id="folders" v-if="folders.length > 0">
      <!-- Top-level folders: always visible -->
      <div class="folderTop">
        <a
          href="#"
          v-bind:class="{ folderTab: true, active: currentFolder === '' }"
          v-on:click.prevent="selectFolder('')"
          >{{ i18n.all_folders }}</a
        >
        <a
          href="#"
          v-for="top in topFolders"
          :key="top.path"
          v-bind:class="{ folderTab: true, active: isUnderFolder(top.path) }"
          v-on:click.prevent="selectFolder(top.path)"
        >
          <IconFolder />
          {{ top.name }}
        </a>
        <a
          href="#"
          v-bind:class="{
            folderTab: true,
            unfiled: true,
            active: currentFolder === NO_FOLDER,
          }"
          v-if="hasUnfiledEntries"
          v-on:click.prevent="selectFolder(NO_FOLDER)"
          >{{ i18n.no_folder }}</a
        >
      </div>
      <!-- Inside a folder: breadcrumb (from 2nd level) + sub-folders -->
      <div
        class="folderSub"
        v-if="breadcrumbs.length > 1 || childFolders.length > 0"
      >
        <div class="folderPath" v-if="breadcrumbs.length > 1">
          <template v-for="(crumb, i) in breadcrumbs">
            <span class="crumbSep" v-if="i > 0" :key="crumb.path + '-sep'"
              >›</span
            >
            <a
              href="#"
              :key="crumb.path"
              v-bind:class="{
                crumb: true,
                active: currentFolder === crumb.path,
              }"
              v-on:click.prevent="selectFolder(crumb.path)"
              >{{ crumb.name }}</a
            >
          </template>
        </div>
        <div class="folderChildren" v-if="childFolders.length > 0">
          <a
            href="#"
            v-for="child in childFolders"
            :key="child.path"
            class="folderTab child"
            v-on:click.prevent="selectFolder(child.path)"
          >
            <IconFolder />
            {{ child.name }}
          </a>
        </div>
      </div>
    </div>
    <datalist id="folderList">
      <option v-for="name in folders" :key="name" v-bind:value="name"></option>
    </datalist>
    <!-- Entries -->
    <div
      v-dragula
      drake="entryDrake"
      v-on:keydown.down="focusNextEntry()"
      v-on:keydown.right="focusNextEntry()"
      v-on:keydown.up="focusLastEntry()"
      v-on:keydown.left="focusLastEntry()"
    >
      <EntryComponent
        v-for="entry in entries"
        :key="entry.hash"
        v-bind:filtered="!entry.pinned && !isMatchedEntry(entry)"
        v-bind:notSearched="!isSearchedEntry(entry)"
        v-bind:notInFolder="!isInCurrentFolder(entry)"
        v-bind:entry="entry"
        v-bind:tabindex="getTabindex(entry)"
      />
      <div class="no-entry" v-if="entries.length === 0 && initComplete">
        <IconKey />
        <p>
          {{ i18n.no_entires }}
          <a href="#" v-on:click="openLink('https://otp.ee/quickstart')">{{
            i18n.learn_more
          }}</a>
        </p>
      </div>
    </div>
  </div>
</template>
<script lang="ts">
import Vue from "vue";
import { mapState, mapGetters } from "vuex";
import { OTPEntry } from "../../models/otp";
import { EntryStorage } from "../../models/storage";

import EntryComponent from "./EntryComponent.vue";
import { FOLDER_SEPARATOR } from "../../models/otp";
import IconFolder from "../../../svg/folder.svg";

// import IconPlus from "../../../svg/plus.svg";
import IconKey from "../../../svg/key-solid.svg";

const computed: {
  filter: () => boolean;
  showSearch: () => boolean;
  shouldFilter: () => boolean;
  entries: () => OTPEntry[];
  folders: () => string[];
  currentFolder: () => string;
  hasUnfiledEntries: () => boolean;
  topFolders: () => { name: string; path: string }[];
  breadcrumbs: () => { name: string; path: string }[];
  childFolders: () => { name: string; path: string }[];
  style: () => { isEditing: boolean };
} = {
  ...mapState("style", ["style"]),
  ...mapState("accounts", [
    "filter",
    "showSearch",
    "initComplete",
    "currentFolder",
  ]),
  ...mapGetters("accounts", ["shouldFilter", "entries", "folders"]),
  hasUnfiledEntries(this: { entries: OTPEntry[] }) {
    return this.entries.some((entry) => !entry.folder);
  },
  topFolders(this: { folders: string[] }) {
    return childrenOf("", this.folders);
  },
  breadcrumbs(this: { currentFolder: string }) {
    if (this.currentFolder === "" || this.currentFolder === NO_FOLDER) {
      return [];
    }
    const segments = this.currentFolder.split(FOLDER_SEPARATOR);
    return segments.map((name, i) => ({
      name,
      path: segments.slice(0, i + 1).join(FOLDER_SEPARATOR),
    }));
  },
  childFolders(this: { currentFolder: string; folders: string[] }) {
    if (this.currentFolder === "" || this.currentFolder === NO_FOLDER) {
      return [];
    }
    return childrenOf(this.currentFolder, this.folders);
  },
};

/** Direct sub-folders of `parent` ("" = root) among all folder paths. */
function childrenOf(parent: string, folders: string[]) {
  const prefix = parent === "" ? "" : parent + FOLDER_SEPARATOR;
  const seen = new Set<string>();
  const children: { name: string; path: string }[] = [];
  for (const path of folders) {
    if (prefix !== "" && !path.startsWith(prefix)) {
      continue;
    }
    const name = path.slice(prefix.length).split(FOLDER_SEPARATOR)[0];
    if (!name || seen.has(name)) {
      continue;
    }
    seen.add(name);
    children.push({ name, path: prefix + name });
  }
  return children;
}

// Sentinel for the "unfiled" tab; cannot collide with a real folder name
// because folder names are trimmed and this one contains control chars.
const NO_FOLDER = "\u0000no-folder\u0000";

export default Vue.extend({
  data: function () {
    return {
      searchText: "",
      NO_FOLDER,
    };
  },
  watch: {
    folders(newFolders: string[]) {
      // Selected folder disappeared (renamed/emptied) -> back to "all"
      if (
        this.currentFolder !== "" &&
        this.currentFolder !== NO_FOLDER &&
        !newFolders.includes(this.currentFolder)
      ) {
        // fall back to the nearest ancestor that still exists
        const segments = this.currentFolder.split(FOLDER_SEPARATOR);
        let fallback = "";
        for (let i = segments.length - 1; i > 0; i--) {
          const candidate = segments.slice(0, i).join(FOLDER_SEPARATOR);
          if (newFolders.includes(candidate)) {
            fallback = candidate;
            break;
          }
        }
        this.selectFolder(fallback);
      }
    },
  },
  computed,
  methods: {
    openLink(url: string) {
      window.open(url, "_blank");
      return;
    },
    isMatchedEntry(entry: OTPEntry) {
      for (const hash of this.$store.getters["accounts/matchedEntries"]) {
        if (entry.hash === hash) {
          return true;
        }
      }
      return false;
    },
    isSearchedEntry(entry: OTPEntry) {
      if (this.searchText === "") {
        return true;
      }
      if (
        entry.issuer.toLowerCase().includes(this.searchText.toLowerCase()) ||
        entry.account.toLowerCase().includes(this.searchText.toLowerCase())
      ) {
        return true;
      } else {
        return false;
      }
    },
    clearFilter() {
      this.$store.dispatch("accounts/clearFilter");
    },
    selectFolder(folder: string) {
      this.$store.commit("accounts/setFolder", folder);
      const codesEl = document.getElementById("codes") as HTMLDivElement;
      if (codesEl) {
        codesEl.scrollTop = 0;
      }
    },
    isUnderFolder(folder: string) {
      return (
        this.currentFolder === folder ||
        this.currentFolder.startsWith(folder + FOLDER_SEPARATOR)
      );
    },
    isInCurrentFolder(entry: OTPEntry) {
      // While editing, show every entry so folders can be assigned freely
      if (this.style.isEditing || this.currentFolder === "") {
        return true;
      }
      if (this.currentFolder === NO_FOLDER) {
        return !entry.folder;
      }
      // A folder shows its own entries and everything in its sub-folders
      return (
        entry.folder === this.currentFolder ||
        entry.folder.startsWith(this.currentFolder + FOLDER_SEPARATOR)
      );
    },
    isEntryVisible(entry: OTPEntry) {
      return (
        this.isSearchedEntry(entry) &&
        this.isInCurrentFolder(entry) &&
        (entry.pinned ||
          !this.shouldFilter ||
          !this.filter ||
          this.isMatchedEntry(entry))
      );
    },
    getTabindex(entry: OTPEntry) {
      const firstEntry = this.entries.find((entry) =>
        this.isEntryVisible(entry)
      );

      return entry === firstEntry ? 0 : -1;
    },
    findNextEntryIndex(reverse: boolean) {
      if (document.activeElement?.getAttribute("data-x-role") !== "entry") {
        return -1;
      }

      const activeIndex = Array.prototype.indexOf.call(
        document.querySelectorAll(".entry"),
        document.activeElement
      );
      if (activeIndex === -1) {
        return -1;
      }

      // reverse modify origin array, and use slice() to make a clone first
      const _entries = reverse ? this.entries.slice().reverse() : this.entries;

      let nextIndex = _entries.findIndex(
        (entry, index) =>
          index >
            (reverse ? this.entries.length - 1 - activeIndex : activeIndex) &&
          this.isEntryVisible(entry)
      );

      if (nextIndex === -1) {
        nextIndex = _entries.findIndex((entry) => this.isEntryVisible(entry));
      }

      return nextIndex;
    },
    focusNextEntry() {
      const nextIndex = this.findNextEntryIndex(false);
      document
        .querySelector<HTMLLinkElement>(`.entry:nth-child(${nextIndex + 1})`)
        ?.focus();
    },
    focusLastEntry() {
      const lastIndex = this.entries.length - 1 - this.findNextEntryIndex(true);
      document
        .querySelector<HTMLLinkElement>(`.entry:nth-child(${lastIndex + 1})`)
        ?.focus();
    },
  },
  created() {
    // Don't drag if !isEditing
    this.$dragula.$service.options("entryDrake", {
      invalid: () => {
        if (!this.$store.state.style.style.isEditing) {
          return true;
        } else {
          return false;
        }
      },
    });

    // Update entry index if dragged
    this.$dragula.$service.eventBus.$on(
      "dropModel",
      async ({
        dragIndex,
        dropIndex,
      }: {
        dragIndex: number;
        dropIndex: number;
      }) => {
        this.$store.commit("accounts/moveCode", {
          from: dragIndex,
          to: dropIndex,
        });
        await EntryStorage.set(this.$store.state.accounts.entries);
      }
    );
  },
  components: {
    EntryComponent,
    // IconPlus,
    IconKey,
    IconFolder,
  },
});
</script>
