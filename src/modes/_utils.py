def get_hints(domain_name: str, img: bool = True) -> str:
    if domain_name not in (
        "blocksworld",
        "blocksworld_front_side",
        "blocksworld_front_top",
        "kitchen",
    ):
        print(
            f"WARNING: no hint information available for domain '{domain_name}'; not including in prompt"
        )
        return ""
    if domain_name.startswith("blocksworld"):
        if img:
            return (
                "Hints:\n"
                "- If no robot arm or gripper is visible in the image, assume the gripper is empty and not holding any object.\n"
                "- The predicate (on ?x - block ?y - block) is defined as block x is on block y."
            )
        else:
            return (
                "Hints:\n"
                "- The predicate (on ?x - block ?y - block) is defined as block x is on block y."
            )
    else:
        if img:
            return (
                "Hints:\n"
                "- Assume the robot's gripper is empty and not holding any object."
            )
        else:
            return ""


def get_views(domain_name: str) -> str:
    if domain_name not in (
        "blocksworld_front_side",
        "blocksworld_front_top",
        "kitchen",
    ):
        print(
            f"WARNING: no view information available for domain '{domain_name}'; not including in prompt"
        )
        return ""
    if domain_name.endswith("front_side"):
        return (
            "Views:\n"
            "- The first image is a FRONT VIEW: the camera points horizontally at the "
            "scene. The image's vertical axis is height (up/down in the world); the "
            "horizontal axis is left/right.\n"
            "- The second image is a SIDE VIEW: the camera also points horizontally "
            "at the scene, but rotated 90 degrees about the vertical (up) axis "
            "relative to the front-view camera, so its optical axis is perpendicular "
            "to the front view's. The image's vertical axis is height (up/down in "
            "the world), matching the front view. The horizontal axis corresponds "
            "to depth (left of image = farther from the front-view camera; right of "
            "image = closer to it). What was left/right in the front view is now "
            "into/out of the page."
        )
    elif domain_name.endswith("front_top"):
        return (
            "Views:\n"
            "- The first image is a FRONT VIEW: the camera points horizontally at the "
            "scene. The image's vertical axis is height (up/down in the world); the "
            "horizontal axis is left/right.\n"
            "- The second image is a TOP VIEW (nadir / plan view): the camera points "
            "straight down, with its optical axis perpendicular to the surface. The "
            "image's vertical axis corresponds to depth (top of image = farther from "
            "the front-view camera; bottom of image = closer to it). The images' "
            "horizontal axis is left/right, matching the front view."
        )
    else:
        return (
            "Views:\n"
            "- The first image is a THIRD-PERSON SCENE VIEW, capturing the full environment and the robot's body from a distance.\n"
            "- The second image is a WRIST-MOUNTED VIEW, showing the robot's gripper from a close-up perspective."
        )


def get_views_simple(domain_name: str) -> str:
    if domain_name not in (
        "blocksworld_front_side",
        "blocksworld_front_top",
        "kitchen",
    ):
        print(
            f"WARNING: no view information available for domain '{domain_name}'; not including in prompt"
        )
        return ""
    if domain_name.endswith("front_side"):
        return (
            "Views:\n"
            "- The first image is a front view.\n"
            "- The second image is a side view."
        )
    elif domain_name.endswith("front_top"):
        return (
            "Views:\n"
            "- The first image is a front view.\n"
            "- The second image is a top view (nadir / plan view)."
        )
    else:
        return (
            "Views:\n"
            "- The first image is a third-person scene view.\n"
            "- The second image is a wrist-mounted view."
        )
