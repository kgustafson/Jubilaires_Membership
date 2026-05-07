(() => {
  const normalize = (value) => (value || "").toString().trim().toLowerCase();

  const cellValue = (row, index) => normalize(row.cells[index]?.textContent);

  const compareRows = (index, type, direction) => (left, right) => {
    let leftValue = cellValue(left, index);
    let rightValue = cellValue(right, index);

    if (type === "date") {
      leftValue = leftValue ? Date.parse(leftValue) : Number.POSITIVE_INFINITY;
      rightValue = rightValue ? Date.parse(rightValue) : Number.POSITIVE_INFINITY;
    }

    const result = leftValue > rightValue ? 1 : leftValue < rightValue ? -1 : 0;
    return direction === "ascending" ? result : -result;
  };

  const updateCount = (table) => {
    const rows = [...table.tBodies[0].querySelectorAll("tr[data-search]")];
    const visibleRows = rows.filter((row) => !row.hidden).length;
    const countTarget = table.closest(".table-section")?.querySelector("[data-roster-count]");

    if (countTarget) {
      countTarget.textContent = `${visibleRows} shown`;
    }
  };

  const rowMatchesCategory = (row, filterType, filterValue) => {
    const normalizedValue = normalize(filterValue);

    if (filterType === "all") {
      return true;
    }

    if (filterType === "status") {
      return normalize(row.dataset.status) === normalizedValue;
    }

    if (filterType === "part") {
      const parts = normalize(row.dataset.parts).split(",").map((part) => part.trim());
      return parts.includes(normalizedValue);
    }

    return true;
  };

  const applyTableState = (table) => {
    const filterType = table.dataset.filterType || "all";
    const filterValue = table.dataset.filterValue || "";
    const query = normalize(table.dataset.searchQuery);

    table.tBodies[0].querySelectorAll("tr[data-search]").forEach((row) => {
      const matchesCategory = rowMatchesCategory(row, filterType, filterValue);
      const matchesSearch = !query || normalize(row.dataset.search).includes(query);
      row.hidden = !(matchesCategory && matchesSearch);
    });

    updateCount(table);
  };

  const applyFilter = (table, filterType, filterValue) => {
    table.dataset.filterType = filterType || "all";
    table.dataset.filterValue = filterValue || "";
    applyTableState(table);
  };

  const wireSorting = (table) => {
    table.querySelectorAll("[data-sort-index]").forEach((button) => {
      button.addEventListener("click", () => {
        const index = Number(button.dataset.sortIndex);
        const type = button.dataset.sortType || "text";
        const currentDirection = button.dataset.sortDirection || "descending";
        const nextDirection = currentDirection === "ascending" ? "descending" : "ascending";
        const rows = [...table.tBodies[0].querySelectorAll("tr[data-search]")];

        table.querySelectorAll("th").forEach((header) => header.setAttribute("aria-sort", "none"));
        table.querySelectorAll("[data-sort-index]").forEach((sortButton) => {
          sortButton.dataset.sortDirection = "";
          sortButton.classList.remove("ascending", "descending");
        });

        button.dataset.sortDirection = nextDirection;
        button.classList.add(nextDirection);
        button.closest("th")?.setAttribute("aria-sort", nextDirection);

        rows.sort(compareRows(index, type, nextDirection)).forEach((row) => table.tBodies[0].append(row));
      });
    });
  };

  const wireMetricFilters = (table) => {
    document.querySelectorAll("[data-roster-filter]").forEach((metric) => {
      metric.addEventListener("click", (event) => {
        event.preventDefault();
        const wasActive = metric.classList.contains("active");
        const filterType = metric.dataset.rosterFilter;
        const shouldClearFilter = wasActive && filterType !== "all";

        document.querySelectorAll("[data-roster-filter]").forEach((item) => {
          item.classList.remove("active");
          item.setAttribute("aria-pressed", "false");
        });

        if (shouldClearFilter) {
          const allMetric = document.querySelector('[data-roster-filter="all"]');
          allMetric?.classList.add("active");
          allMetric?.setAttribute("aria-pressed", "true");
          applyFilter(table, "all", "");
          return;
        }

        metric.classList.add("active");
        metric.setAttribute("aria-pressed", "true");
        applyFilter(table, filterType, metric.dataset.rosterValue);
      });
    });
  };

  const wireRosterSearch = (table) => {
    document.querySelectorAll("[data-roster-search]").forEach((input) => {
      const applySearch = () => {
        table.dataset.searchQuery = input.value;
        applyTableState(table);
      };

      input.addEventListener("input", applySearch);
      input.addEventListener("search", applySearch);
    });

    document.querySelectorAll("[data-roster-search-form]").forEach((form) => {
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        const input = form.querySelector("[data-roster-search]");
        if (input) {
          table.dataset.searchQuery = input.value;
          applyTableState(table);
        }
      });
    });
  };

  document.querySelectorAll("[data-member-table]").forEach((table) => {
    table.dataset.filterType = "all";
    table.dataset.filterValue = "";
    table.dataset.searchQuery = "";
    wireSorting(table);
    wireMetricFilters(table);
    wireRosterSearch(table);
    updateCount(table);
  });

  document.querySelectorAll("[data-open-dialog]").forEach((button) => {
    button.addEventListener("click", () => {
      document.getElementById(button.dataset.openDialog)?.showModal();
    });
  });

  document.querySelectorAll("[data-close-dialog]").forEach((button) => {
    button.addEventListener("click", () => {
      button.closest("dialog")?.close();
    });
  });

  const setPreview = (picker, fileOrUrl) => {
    const preview = picker.querySelector("[data-photo-preview]");
    const empty = picker.querySelector("[data-photo-empty]");
    if (!preview) {
      return;
    }

    if (fileOrUrl instanceof File) {
      preview.src = URL.createObjectURL(fileOrUrl);
    } else {
      preview.src = fileOrUrl || "";
    }
    preview.hidden = !preview.src;
    if (empty) {
      empty.hidden = Boolean(preview.src);
    }
  };

  const setFileInput = (input, file) => {
    const transfer = new DataTransfer();
    transfer.items.add(file);
    input.files = transfer.files;
    input.dispatchEvent(new Event("change", { bubbles: true }));
  };

  document.querySelectorAll(".photo-picker").forEach((picker) => {
    const dropzone = picker.querySelector("[data-photo-dropzone]");
    const fileInput = picker.querySelector("[data-photo-file]");
    if (!dropzone || !fileInput) {
      return;
    }

    fileInput.addEventListener("change", () => {
      const file = fileInput.files?.[0];
      if (file) {
        picker.querySelectorAll('input[name="selected_photo_path"]').forEach((input) => {
          input.checked = false;
        });
        setPreview(picker, file);
      }
    });

    picker.querySelectorAll('input[name="selected_photo_path"]').forEach((input) => {
      input.addEventListener("change", () => {
        fileInput.value = "";
        setPreview(picker, input.value);
      });
    });

    ["dragenter", "dragover"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropzone.classList.add("active");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropzone.addEventListener(eventName, () => {
        dropzone.classList.remove("active");
      });
    });

    dropzone.addEventListener("drop", (event) => {
      event.preventDefault();
      const file = [...event.dataTransfer.files].find((item) => item.type.startsWith("image/"));
      if (file) {
        setFileInput(fileInput, file);
      }
    });

    dropzone.addEventListener("paste", (event) => {
      const file = [...event.clipboardData.files].find((item) => item.type.startsWith("image/"));
      if (file) {
        event.preventDefault();
        setFileInput(fileInput, file);
      }
    });
  });

  document.querySelectorAll("[data-photo-target-type]").forEach((select) => {
    const form = select.closest("form");
    const updateTarget = () => {
      const assigningFamily = select.value === "family";
      form.querySelector("[data-member-target]")?.toggleAttribute("hidden", assigningFamily);
      form.querySelector("[data-family-target]")?.toggleAttribute("hidden", !assigningFamily);
    };
    select.addEventListener("change", updateTarget);
    updateTarget();
  });
})();
