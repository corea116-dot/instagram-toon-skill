"""Shared page slots; panel coordinates are local to these frames."""

def grid_geometry(
    count: int,
) -> tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]:
    match count:
        case 2:
            return ((1008, 630), (1008, 630)), ((36, 30), (36, 690))
        case 3:
            return (
                ((1008, 594), (492, 660), (492, 660)),
                ((36, 30), (36, 660), (552, 660)),
            )
        case 4:
            return (
                ((492, 621),) * 4,
                ((36, 30), (552, 30), (36, 699), (552, 699)),
            )
        case _:
            raise ValueError(f"unsupported page layout: {count} panels")


def panel_sizes(output_layout):
    return tuple(size for count in output_layout for size in (((1080, 1350),) if count == 1 else grid_geometry(count)[0]))
