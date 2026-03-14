import cv2
import numpy as np
import os


import cv2
import numpy as np
import os


def match_templates(
    image,
    template_dir,
    scales,
    threshold,
    draw
):
    """
    Retourne :
    - matches      : liste de tous les matchs >= threshold
    - image_color  : image debug (ou None)
    - best_symbol  : label avec le score MAX (ou None)
    """

    # =============================
    # NORMALISATION IMAGE
    # =============================
    if image.ndim == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if image.dtype != np.uint8:
        image = image.astype(np.uint8)

    image_color = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) if draw else None

    matches = []

    best_score = 0
    best_symbol = None
    best_loc = None
    best_size = None

    # =============================
    # BOUCLE TEMPLATES + SCALES
    # =============================
    for root, _, files in os.walk(template_dir):
        for file in files:
            if not file.lower().endswith(".png"):
                continue

            label = os.path.splitext(file)[0]
            path = os.path.join(root, file)

            template = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if template is None:
                continue

            if template.dtype != np.uint8:
                template = template.astype(np.uint8)

            for scale in scales:
                resized = cv2.resize(
                    template,
                    None,
                    fx=scale,
                    fy=scale,
                    interpolation=cv2.INTER_AREA
                )

                h, w = resized.shape
                if h >= image.shape[0] or w >= image.shape[1]:
                    continue

                res = cv2.matchTemplate(
                    image,
                    resized,
                    cv2.TM_CCOEFF_NORMED
                )

                _, max_val, _, max_loc = cv2.minMaxLoc(res)

                if max_val >= threshold:
                    match = {
                        "label": label,
                        "score": float(max_val),
                        "loc": max_loc,
                        "size": (h, w)
                    }
                    matches.append(match)

                    # 🔥 MEILLEUR MATCH GLOBAL
                    if max_val > best_score:
                        best_score = max_val
                        best_symbol = label
                        best_loc = max_loc
                        best_size = (h, w)

    # =============================
    # DESSIN
    # =============================
    if draw and best_symbol is not None:
        h, w = best_size
        tl = best_loc
        br = (tl[0] + w, tl[1] + h)

        cv2.rectangle(image_color, tl, br, (0, 0, 255), 3)
        cv2.putText(
            image_color,
            best_symbol,
            (tl[0], tl[1] - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )

    return matches, image_color, best_symbol