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

  const applyFilter = (table, filterType, filterValue) => {
    const normalizedValue = normalize(filterValue);

    table.tBodies[0].querySelectorAll("tr[data-search]").forEach((row) => {
      if (filterType === "all") {
        row.hidden = false;
        return;
      }

      if (filterType === "status") {
        row.hidden = normalize(row.dataset.status) !== normalizedValue;
        return;
      }

      if (filterType === "part") {
        const parts = normalize(row.dataset.parts).split(",").map((part) => part.trim());
        row.hidden = !parts.includes(normalizedValue);
      }
    });

    updateCount(table);
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

        document.querySelectorAll("[data-roster-filter]").forEach((item) => {
          item.classList.remove("active");
          item.setAttribute("aria-pressed", "false");
        });

        metric.classList.add("active");
        metric.setAttribute("aria-pressed", "true");
        applyFilter(table, metric.dataset.rosterFilter, metric.dataset.rosterValue);
      });
    });
  };

  document.querySelectorAll("[data-member-table]").forEach((table) => {
    wireSorting(table);
    wireMetricFilters(table);
    updateCount(table);
  });
})();
