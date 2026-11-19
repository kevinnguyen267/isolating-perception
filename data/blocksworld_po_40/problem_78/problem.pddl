(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue_1 - block
		blue_2 - block
		blue_3 - block
		blue_4 - block
		blue_5 - block
		blue_6 - block
		blue_7 - block
		green_1 - block
		green_2 - block
		green_3 - block
		green_4 - block
		green_5 - block
		green_6 - block
		green_7 - block
		orange_1 - block
		orange_2 - block
		orange_3 - block
		orange_4 - block
		orange_5 - block
		orange_6 - block
		purple_1 - block
		purple_2 - block
		purple_3 - block
		purple_4 - block
		purple_5 - block
		purple_6 - block
		purple_7 - block
		red_1 - block
		red_2 - block
		red_3 - block
		red_4 - block
		red_5 - block
		red_6 - block
		yellow_1 - block
		yellow_2 - block
		yellow_3 - block
		yellow_4 - block
		yellow_5 - block
		yellow_6 - block
		yellow_7 - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable purple_3)
		(on orange_2 purple_3)
		(on yellow_3 orange_2)
		(on orange_3 yellow_3)
		(on purple_7 orange_3)
		(on red_5 purple_7)
		(on green_6 red_5)
		(clear green_6)

		(ontable green_3)
		(on red_1 green_3)
		(on purple_1 red_1)
		(on yellow_7 purple_1)
		(on blue_1 yellow_7)
		(on purple_5 blue_1)
		(on red_6 purple_5)
		(clear red_6)

		(ontable purple_2)
		(on red_3 purple_2)
		(on yellow_1 red_3)
		(on orange_4 yellow_1)
		(on blue_4 orange_4)
		(on orange_5 blue_4)
		(on blue_3 orange_5)
		(clear blue_3)

		(ontable yellow_2)
		(on blue_7 yellow_2)
		(on blue_6 blue_7)
		(on blue_2 blue_6)
		(on blue_5 blue_2)
		(on green_7 blue_5)
		(clear green_7)

		(ontable green_2)
		(on yellow_4 green_2)
		(on yellow_6 yellow_4)
		(on orange_1 yellow_6)
		(on purple_6 orange_1)
		(on red_4 purple_6)
		(clear red_4)

		(ontable green_4)
		(on red_2 green_4)
		(on green_5 red_2)
		(on green_1 green_5)
		(on yellow_5 green_1)
		(on purple_4 yellow_5)
		(on orange_6 purple_4)
		(clear orange_6)
	)
	(:goal (and (handempty robot)
		(ontable blue_7)
		(on purple_1 blue_7)
		(on green_6 purple_1)
		(on orange_6 green_6)
		(on yellow_7 orange_6)
		(on blue_6 yellow_7)
		(on red_4 blue_6)
		(clear red_4)

		(ontable orange_1)
		(on red_3 orange_1)
		(on red_1 red_3)
		(on red_6 red_1)
		(on green_1 red_6)
		(on purple_2 green_1)
		(on green_2 purple_2)
		(clear green_2)

		(ontable orange_4)
		(on red_5 orange_4)
		(on red_2 red_5)
		(on purple_6 red_2)
		(on blue_1 purple_6)
		(on blue_2 blue_1)
		(on yellow_2 blue_2)
		(clear yellow_2)

		(ontable purple_4)
		(on purple_3 purple_4)
		(on orange_2 purple_3)
		(on purple_7 orange_2)
		(on green_5 purple_7)
		(on yellow_5 green_5)
		(clear yellow_5)

		(ontable blue_5)
		(on yellow_4 blue_5)
		(on green_3 yellow_4)
		(on blue_4 green_3)
		(on green_4 blue_4)
		(on yellow_6 green_4)
		(clear yellow_6)

		(ontable yellow_3)
		(on yellow_1 yellow_3)
		(on purple_5 yellow_1)
		(on blue_3 purple_5)
		(on orange_3 blue_3)
		(on green_7 orange_3)
		(on orange_5 green_7)
		(clear orange_5)
	))
)