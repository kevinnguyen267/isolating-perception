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
		(ontable red_2)
		(on blue_6 red_2)
		(on purple_3 blue_6)
		(on blue_2 purple_3)
		(on yellow_3 blue_2)
		(on blue_3 yellow_3)
		(on green_7 blue_3)
		(clear green_7)

		(ontable purple_6)
		(on yellow_7 purple_6)
		(on yellow_2 yellow_7)
		(on red_5 yellow_2)
		(on green_3 red_5)
		(on red_1 green_3)
		(on orange_6 red_1)
		(clear orange_6)

		(ontable yellow_5)
		(on blue_4 yellow_5)
		(on red_3 blue_4)
		(on red_4 red_3)
		(on orange_5 red_4)
		(on green_4 orange_5)
		(on green_1 green_4)
		(clear green_1)

		(ontable purple_7)
		(on blue_7 purple_7)
		(on orange_1 blue_7)
		(on blue_1 orange_1)
		(on yellow_4 blue_1)
		(on blue_5 yellow_4)
		(clear blue_5)

		(ontable orange_2)
		(on green_2 orange_2)
		(on green_6 green_2)
		(on orange_4 green_6)
		(on purple_2 orange_4)
		(on yellow_6 purple_2)
		(clear yellow_6)

		(ontable yellow_1)
		(on purple_4 yellow_1)
		(on orange_3 purple_4)
		(on green_5 orange_3)
		(on purple_1 green_5)
		(on red_6 purple_1)
		(on purple_5 red_6)
		(clear purple_5)
	)
	(:goal (and (handempty robot)
		(ontable red_3)
		(on yellow_2 red_3)
		(on blue_5 yellow_2)
		(on yellow_6 blue_5)
		(on purple_5 yellow_6)
		(on blue_2 purple_5)
		(on red_6 blue_2)
		(clear red_6)

		(ontable orange_5)
		(on red_5 orange_5)
		(on blue_1 red_5)
		(on purple_2 blue_1)
		(on blue_6 purple_2)
		(on blue_3 blue_6)
		(on purple_1 blue_3)
		(clear purple_1)

		(ontable green_7)
		(on blue_7 green_7)
		(on green_5 blue_7)
		(on orange_3 green_5)
		(on orange_1 orange_3)
		(on green_4 orange_1)
		(on green_6 green_4)
		(clear green_6)

		(ontable yellow_4)
		(on yellow_3 yellow_4)
		(on red_4 yellow_3)
		(on yellow_5 red_4)
		(on green_3 yellow_5)
		(on purple_3 green_3)
		(clear purple_3)

		(ontable yellow_1)
		(on blue_4 yellow_1)
		(on orange_6 blue_4)
		(on purple_4 orange_6)
		(on yellow_7 purple_4)
		(on green_2 yellow_7)
		(clear green_2)

		(ontable orange_4)
		(on purple_7 orange_4)
		(on red_2 purple_7)
		(on orange_2 red_2)
		(on red_1 orange_2)
		(on purple_6 red_1)
		(on green_1 purple_6)
		(clear green_1)
	))
)