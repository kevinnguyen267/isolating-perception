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
		(ontable orange_1)
		(on purple_5 orange_1)
		(on red_1 purple_5)
		(on green_7 red_1)
		(on purple_6 green_7)
		(on green_1 purple_6)
		(on yellow_5 green_1)
		(clear yellow_5)

		(ontable yellow_2)
		(on yellow_3 yellow_2)
		(on purple_4 yellow_3)
		(on red_5 purple_4)
		(on purple_2 red_5)
		(on yellow_7 purple_2)
		(on blue_6 yellow_7)
		(clear blue_6)

		(ontable yellow_6)
		(on blue_4 yellow_6)
		(on yellow_4 blue_4)
		(on green_4 yellow_4)
		(on green_2 green_4)
		(on blue_5 green_2)
		(on orange_4 blue_5)
		(clear orange_4)

		(ontable orange_6)
		(on purple_3 orange_6)
		(on red_3 purple_3)
		(on purple_7 red_3)
		(on green_3 purple_7)
		(on blue_2 green_3)
		(clear blue_2)

		(ontable blue_7)
		(on red_2 blue_7)
		(on green_5 red_2)
		(on blue_1 green_5)
		(on blue_3 blue_1)
		(on red_4 blue_3)
		(clear red_4)

		(ontable orange_5)
		(on green_6 orange_5)
		(on yellow_1 green_6)
		(on orange_3 yellow_1)
		(on orange_2 orange_3)
		(on red_6 orange_2)
		(on purple_1 red_6)
		(clear purple_1)
	)
	(:goal (and (handempty robot)
		(ontable green_1)
		(on green_2 green_1)
		(on green_3 green_2)
		(on green_4 green_3)
		(on green_5 green_4)
		(on green_6 green_5)
		(on green_7 green_6)
		(clear green_7)

		(ontable blue_1)
		(on blue_2 blue_1)
		(on blue_3 blue_2)
		(on blue_4 blue_3)
		(on blue_5 blue_4)
		(on blue_6 blue_5)
		(on blue_7 blue_6)
		(clear blue_7)

		(ontable purple_1)
		(on purple_2 purple_1)
		(on purple_3 purple_2)
		(on purple_4 purple_3)
		(on purple_5 purple_4)
		(on purple_6 purple_5)
		(on purple_7 purple_6)
		(clear purple_7)

		(ontable yellow_1)
		(on yellow_2 yellow_1)
		(on yellow_3 yellow_2)
		(on yellow_4 yellow_3)
		(on yellow_5 yellow_4)
		(on yellow_6 yellow_5)
		(on yellow_7 yellow_6)
		(clear yellow_7)

		(ontable red_1)
		(on red_2 red_1)
		(on red_3 red_2)
		(on red_4 red_3)
		(on red_5 red_4)
		(on red_6 red_5)
		(clear red_6)

		(ontable orange_1)
		(on orange_2 orange_1)
		(on orange_3 orange_2)
		(on orange_4 orange_3)
		(on orange_5 orange_4)
		(on orange_6 orange_5)
		(clear orange_6)
	))
)