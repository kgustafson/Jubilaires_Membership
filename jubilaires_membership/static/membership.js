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

    if (type === "number") {
      leftValue = leftValue ? Number(leftValue) : Number.POSITIVE_INFINITY;
      rightValue = rightValue ? Number(rightValue) : Number.POSITIVE_INFINITY;
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

  const rowIsActive = (row) => normalize(row.dataset.status) === "active";

  const rowIncludedByStatus = (row, showInactive) => showInactive || rowIsActive(row);

  const rowHasPart = (row, partName) => {
    const normalizedPart = normalize(partName);
    const parts = normalize(row.dataset.parts).split(",").map((part) => part.trim());
    return parts.includes(normalizedPart);
  };

  const updateMetricCounts = (table) => {
    const showInactive = table.dataset.showInactive === "true";
    const rows = [...table.tBodies[0].querySelectorAll("tr[data-search]")]
      .filter((row) => rowIncludedByStatus(row, showInactive));

    const counts = {
      members: rows.length,
      tenor: rows.filter((row) => rowHasPart(row, "Tenor")).length,
      lead: rows.filter((row) => rowHasPart(row, "Lead")).length,
      baritone: rows.filter((row) => rowHasPart(row, "Baritone")).length,
      bass: rows.filter((row) => rowHasPart(row, "Bass")).length,
    };

    Object.entries(counts).forEach(([key, value]) => {
      document.querySelectorAll(`[data-metric-count="${key}"]`).forEach((target) => {
        target.textContent = value;
      });
    });
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
      return rowHasPart(row, normalizedValue);
    }

    return true;
  };

  const applyTableState = (table) => {
    const filterType = table.dataset.filterType || "all";
    const filterValue = table.dataset.filterValue || "";
    const showInactive = table.dataset.showInactive === "true";
    const query = normalize(table.dataset.searchQuery);

    table.tBodies[0].querySelectorAll("tr[data-search]").forEach((row) => {
      const matchesStatusScope = rowIncludedByStatus(row, showInactive);
      const matchesCategory = rowMatchesCategory(row, filterType, filterValue);
      const matchesSearch = !query || normalize(row.dataset.search).includes(query);
      row.hidden = !(matchesStatusScope && matchesCategory && matchesSearch);
    });

    updateMetricCounts(table);
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
          applyFilter(table, "all", "");
          return;
        }

        metric.classList.add("active");
        metric.setAttribute("aria-pressed", "true");
        applyFilter(table, filterType, metric.dataset.rosterValue);
      });
    });
  };

  const wireInactiveToggle = (table) => {
    document.querySelectorAll("[data-show-inactive]").forEach((input) => {
      input.addEventListener("change", () => {
        table.dataset.showInactive = input.checked ? "true" : "false";
        applyTableState(table);
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
    table.dataset.showInactive = "false";
    wireSorting(table);
    wireMetricFilters(table);
    wireRosterSearch(table);
    wireInactiveToggle(table);
    applyTableState(table);
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

  const normalizeDegrees = (value) => {
    const parsed = Number(value || 0);
    if (!Number.isFinite(parsed)) {
      return 0;
    }
    return ((Math.round(parsed) % 360) + 360) % 360;
  };

  const wirePhotoRotationControls = (container) => {
    const rotationInput = container.querySelector("[data-photo-rotation]");
    const rangeInput = container.querySelector("[data-photo-rotate-range]");
    const numberInput = container.querySelector("[data-photo-rotate-number]");
    const stepButton = container.querySelector("[data-photo-rotate-step]");
    const preview =
      container.querySelector("[data-photo-preview]") ||
      container.querySelector("[data-review-photo-preview]");

    if (!rotationInput || !rangeInput || !numberInput) {
      return;
    }

    const setRotation = (value) => {
      const degrees = normalizeDegrees(value);
      rotationInput.value = String(degrees);
      rangeInput.value = String(degrees);
      numberInput.value = String(degrees);
      if (preview) {
        preview.style.transform = `rotate(${degrees}deg)`;
      }
    };

    stepButton?.addEventListener("click", () => {
      setRotation(Number(rotationInput.value || 0) + 90);
    });
    rangeInput.addEventListener("input", () => setRotation(rangeInput.value));
    numberInput.addEventListener("input", () => setRotation(numberInput.value));
    setRotation(rotationInput.value);
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

    wirePhotoRotationControls(picker);
  });

  document.querySelectorAll(".photo-rotate-form").forEach((form) => {
    wirePhotoRotationControls(form);
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

  document.querySelectorAll("[data-member-select-search]").forEach((input) => {
    const select = document.getElementById(input.dataset.memberSelectTarget);
    if (!select) {
      return;
    }
    const choices = [...select.options].map((option) => ({
      value: option.value,
      text: option.textContent,
      search: normalize(option.dataset.search || option.textContent),
    }));
    const renderChoices = () => {
      const query = normalize(input.value);
      const selectedValue = select.value;
      select.replaceChildren();
      choices
        .filter((choice) => !query || choice.search.includes(query))
        .forEach((choice) => {
          const option = new Option(choice.text, choice.value);
          option.dataset.search = choice.search;
          option.selected = choice.value === selectedValue;
          select.add(option);
        });
    };
    input.addEventListener("input", () => {
      renderChoices();
    });
  });

  const selectedText = (select) => select?.selectedOptions[0]?.textContent?.trim() || "";
  const checkedLabel = (checkbox) => (checkbox?.checked ? "Primary" : "Secondary");

  const refreshListSummary = (kind) => {
    const summary = document.querySelector(`[data-${kind}-summary-list]`);
    const list = document.querySelector(`[data-list-detail-list][data-list-detail-kind="${kind}"]`);
    if (!summary || !list) {
      return;
    }

    const rows = [...list.querySelectorAll(`[data-list-detail-row][data-list-detail-kind="${kind}"]`)];
    const values = rows
      .map((row) => {
        const primary = row.querySelector("[data-list-display-primary]")?.textContent?.trim();
        const secondary = row.querySelector("[data-list-display-secondary]")?.textContent?.trim();
        return kind === "date" && primary && secondary && secondary !== "Choose a date" ? `${primary}: ${secondary}` : primary;
      })
      .filter((value) => value && !value.startsWith("New ") && !value.startsWith("Select "));
    summary.textContent = values.length ? values.join(kind === "address" ? "\n\n" : ", ") : "None";
  };

  const refreshListDetailRow = (row) => {
    const kind = row.dataset.listDetailKind;
    const primary = row.querySelector("[data-list-display-primary]");
    const secondary = row.querySelector("[data-list-display-secondary]");
    if (!kind || !primary || !secondary) {
      return;
    }

    if (kind === "quartet") {
      const quartetName = selectedText(row.querySelector("[data-quartet-select]")) || "Select quartet";
      const state = selectedText(row.querySelector("[data-quartet-state]")) || "Primary";
      const part = selectedText(row.querySelector("[data-quartet-part]"));
      primary.textContent = quartetName;
      secondary.textContent = [state, part && part !== "No quartet part" ? part : ""].filter(Boolean).join(" · ");
    }

    if (kind === "email") {
      const address = row.querySelector("[data-email-address]")?.value.trim() || "New email";
      const label = row.querySelector("[data-email-label]")?.value.trim();
      const isPrimary = row.querySelector("[data-email-primary]");
      primary.textContent = address;
      secondary.textContent = [checkedLabel(isPrimary), label].filter(Boolean).join(" · ");
    }

    if (kind === "phone") {
      const number = row.querySelector("[data-phone-number]")?.value.trim() || "New phone";
      const type = row.querySelector("[data-phone-type]")?.value.trim();
      const label = row.querySelector("[data-phone-label]")?.value.trim();
      const isPrimary = row.querySelector("[data-phone-primary]");
      primary.textContent = number;
      secondary.textContent = [checkedLabel(isPrimary), type, label].filter(Boolean).join(" · ");
    }

    if (kind === "address") {
      const street = row.querySelector("[data-address-street]")?.value.trim();
      const city = row.querySelector("[data-address-city]")?.value.trim();
      const state = row.querySelector("[data-address-state]")?.value.trim();
      const postal = row.querySelector("[data-address-postal]")?.value.trim();
      const raw = row.querySelector("[data-address-raw]")?.value.trim();
      const type = row.querySelector("[data-address-type]")?.value.trim();
      const isPrimary = row.querySelector("[data-address-primary]");
      const cityState = [city, state].filter(Boolean).join(", ");
      primary.textContent = [street, cityState, postal].filter(Boolean).join("\n") || raw || "New address";
      secondary.textContent = [checkedLabel(isPrimary), type].filter(Boolean).join(" · ");
    }

    if (kind === "date") {
      const type = selectedText(row.querySelector("[data-date-classification]")) || "Select date type";
      const date = row.querySelector("[data-important-date]")?.value.trim() || "Choose a date";
      primary.textContent = type;
      secondary.textContent = date;
    }

    refreshListSummary(kind);
  };

  const refreshDateTypeOptions = () => {
    const rows = [...document.querySelectorAll('[data-list-detail-row][data-list-detail-kind="date"]')];
    const selectedValues = rows
      .map((row) => row.querySelector("[data-date-classification]")?.value)
      .filter(Boolean);
    const allValues = [...(rows[0]?.querySelector("[data-date-classification]")?.options || [])]
      .map((option) => option.value)
      .filter(Boolean);
    rows.forEach((row) => {
      const select = row.querySelector("[data-date-classification]");
      if (!select) {
        return;
      }
      [...select.options].forEach((option) => {
        option.disabled = Boolean(option.value) && option.value !== select.value && selectedValues.includes(option.value);
      });
    });
    document.querySelectorAll('[data-add-list-detail-row][data-list-detail-target="important-date-list"]').forEach((button) => {
      button.disabled = Boolean(allValues.length) && selectedValues.length >= allValues.length;
    });
  };

  const toggleEmptyListDetailState = (list) => {
    const hasRows = Boolean(list.querySelector("[data-list-detail-row]"));
    list.querySelector("[data-empty-list-detail]")?.toggleAttribute("hidden", hasRows);
  };

  const wireListDetailRow = (row) => {
    const fields = row.querySelector(".list-detail-fields");
    const editButton = row.querySelector("[data-edit-list-detail-row]");
    const deleteButton = row.querySelector("[data-delete-list-detail-row]");
    const list = row.closest("[data-list-detail-list]");

    row.querySelectorAll("input, select").forEach((input) => {
      input.addEventListener("input", () => {
        refreshListDetailRow(row);
        if (row.dataset.listDetailKind === "date") {
          refreshDateTypeOptions();
        }
      });
      input.addEventListener("change", () => {
        refreshListDetailRow(row);
        if (row.dataset.listDetailKind === "date") {
          refreshDateTypeOptions();
        }
      });
    });

    editButton?.addEventListener("click", () => {
      fields?.toggleAttribute("hidden");
      row.classList.toggle("editing", !fields?.hasAttribute("hidden"));
    });

    deleteButton?.addEventListener("click", () => {
      const kind = row.dataset.listDetailKind;
      row.remove();
      if (list) {
        toggleEmptyListDetailState(list);
      }
      if (kind) {
        refreshListSummary(kind);
      }
      if (kind === "date") {
        refreshDateTypeOptions();
      }
    });

    refreshListDetailRow(row);
    if (row.dataset.listDetailKind === "date") {
      refreshDateTypeOptions();
    }
  };

  document.querySelectorAll("[data-list-detail-list]").forEach((list) => {
    list.querySelectorAll("[data-list-detail-row]").forEach(wireListDetailRow);
    toggleEmptyListDetailState(list);
    refreshListSummary(list.dataset.listDetailKind);
  });

  document.querySelectorAll("[data-add-list-detail-row]").forEach((button) => {
    button.addEventListener("click", () => {
      const list = document.getElementById(button.dataset.listDetailTarget);
      const template = document.getElementById(button.dataset.listDetailTemplate);
      if (!list || !template || !("innerHTML" in template)) {
        return;
      }

      const key = `new_${Date.now()}`;
      const wrapper = document.createElement("div");
      wrapper.innerHTML = template.innerHTML.replace(/__key__/g, key).trim();
      const row = wrapper.firstElementChild;
      if (!row) {
        return;
      }

      list.querySelector("[data-empty-list-detail]")?.setAttribute("hidden", "");
      list.append(row);
      wireListDetailRow(row);
      toggleEmptyListDetailState(list);
      refreshListSummary(row.dataset.listDetailKind);
      if (row.dataset.listDetailKind === "date") {
        refreshDateTypeOptions();
      }
      row.querySelector("input, select")?.focus();
    });
  });

  const roleDateLabel = (start, end) => `${start || "No start"} to ${end || "Present"}`;

  const roleRowStartTime = (row) => {
    const value = row.querySelector("[data-role-start]")?.value || "";
    return value ? Date.parse(`${value}T00:00:00`) : Number.NEGATIVE_INFINITY;
  };

  const refreshRoleRow = (row) => {
    const select = row.querySelector("[data-role-select]");
    const roleNameInput = row.querySelector("[data-role-name-input]");
    const roleName = select?.selectedOptions[0]?.textContent?.trim() || "Select role";
    const start = row.querySelector("[data-role-start]")?.value || "";
    const end = row.querySelector("[data-role-end]")?.value || "";
    row.querySelector("[data-role-display-name]").textContent = roleName;
    row.querySelector("[data-role-display-dates]").textContent = roleDateLabel(start, end);
    if (roleNameInput) {
      roleNameInput.value = select?.value ? "" : roleName;
    }
  };

  const sortRoleRows = (list) => {
    [...list.querySelectorAll("[data-role-assignment-row]")]
      .sort((left, right) => roleRowStartTime(right) - roleRowStartTime(left))
      .forEach((row) => list.append(row));
  };

  const refreshRoleSummary = () => {
    const summary = document.querySelector("[data-role-summary-list]");
    const list = document.querySelector("[data-role-assignment-list]");
    if (!summary || !list) {
      return;
    }

    const rows = [...list.querySelectorAll("[data-role-assignment-row]")];
    if (!rows.length) {
      summary.textContent = "None";
      return;
    }

    summary.textContent = rows
      .map((row) => {
        const name = row.querySelector("[data-role-display-name]")?.textContent?.trim() || "Role";
        const dates = row.querySelector("[data-role-display-dates]")?.textContent?.trim() || "";
        return dates ? `${name} (${dates})` : name;
      })
      .join("; ");
  };

  const wireRoleRow = (row) => {
    const fields = row.querySelector(".role-assignment-fields");
    const editButton = row.querySelector("[data-edit-role-assignment]");
    const deleteButton = row.querySelector("[data-delete-role-assignment]");
    const list = row.closest("[data-role-assignment-list]");

    row.querySelectorAll("[data-role-select], [data-role-start], [data-role-end]").forEach((input) => {
      input.addEventListener("change", () => {
        refreshRoleRow(row);
        if (list) {
          sortRoleRows(list);
        }
        refreshRoleSummary();
      });
    });

    editButton?.addEventListener("click", () => {
      fields?.toggleAttribute("hidden");
      row.classList.toggle("editing", !fields?.hasAttribute("hidden"));
    });

    deleteButton?.addEventListener("click", () => {
      row.remove();
      list?.querySelector("[data-empty-role-assignments]")?.toggleAttribute(
        "hidden",
        Boolean(list.querySelector("[data-role-assignment-row]")),
      );
      refreshRoleSummary();
    });

    refreshRoleRow(row);
  };

  document.querySelectorAll("[data-role-assignment-list]").forEach((list) => {
    list.querySelectorAll("[data-role-assignment-row]").forEach(wireRoleRow);
    sortRoleRows(list);
    refreshRoleSummary();
  });

  document.querySelectorAll("[data-add-role-assignment]").forEach((button) => {
    button.addEventListener("click", () => {
      const list = document.querySelector("[data-role-assignment-list]");
      const template = document.getElementById("role-assignment-template");
      if (!list || !(template instanceof HTMLTemplateElement)) {
        return;
      }

      const key = `new_${Date.now()}`;
      const wrapper = document.createElement("div");
      wrapper.innerHTML = template.innerHTML.replace(/__key__/g, key).trim();
      const row = wrapper.firstElementChild;
      if (!row) {
        return;
      }

      list.querySelector("[data-empty-role-assignments]")?.setAttribute("hidden", "");
      list.append(row);
      wireRoleRow(row);
      refreshRoleSummary();
      row.querySelector("[data-role-select]")?.focus();
    });
  });
})();
