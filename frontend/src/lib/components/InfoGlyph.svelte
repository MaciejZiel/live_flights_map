<script>
  export let kind = "flight";
  export let size = 16;

  const ICONS = {
    flight: [
      "M3 12h18",
      "M10 6l8 6-8 6 2-6-2-6Z",
    ],
    aircraft: [
      "M3 12h18",
      "M8 9l4 3-4 3",
      "M16 7l5 5-5 5",
    ],
    operator: [
      "M5 20V9l7-5 7 5v11",
      "M9 20v-4h6v4",
      "M8 11h.01",
      "M12 11h.01",
      "M16 11h.01",
    ],
    altitude: [
      "M12 20V5",
      "M7 10l5-5 5 5",
      "M5 20h14",
    ],
    speed: [
      "M5 16a7 7 0 1 1 14 0",
      "M12 12l4-3",
      "M9 18h6",
    ],
    heading: [
      "M12 3l7 18-7-4-7 4 7-18Z",
    ],
    vertical: [
      "M8 4v16",
      "M16 20V4",
      "M5 7l3-3 3 3",
      "M13 17l3 3 3-3",
    ],
    tracking: [
      "M5 17c3-7 5-9 14-10",
      "M5 17h.01",
      "M12 10h.01",
      "M19 7h.01",
    ],
    airports: [
      "M4 18h16",
      "M6 18V8",
      "M12 18V5",
      "M18 18V10",
      "M4 8h4",
      "M10 5h4",
      "M16 10h4",
    ],
    route: [
      "M5 7h4",
      "M15 17h4",
      "M9 7c4 0 4 10 8 10",
    ],
  };

  $: iconPaths = ICONS[kind] ?? ICONS.flight;
</script>

<svg
  aria-hidden="true"
  class="info-glyph"
  fill="none"
  height={size}
  stroke="currentColor"
  stroke-linecap="round"
  stroke-linejoin="round"
  stroke-width="1.7"
  viewBox="0 0 24 24"
  width={size}
>
  {#each iconPaths as path}
    <path d={path}></path>
  {/each}
</svg>

<style>
  .info-glyph {
    display: block;
    flex: none;
  }
</style>
