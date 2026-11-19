(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue_1 - block
		blue_2 - block
		blue_3 - block
		green_1 - block
		green_2 - block
		green_3 - block
		green_4 - block
		orange_1 - block
		orange_2 - block
		orange_3 - block
		purple_1 - block
		purple_2 - block
		purple_3 - block
		red_1 - block
		red_2 - block
		red_3 - block
		yellow_1 - block
		yellow_2 - block
		yellow_3 - block
		yellow_4 - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable yellow_2)
		(on green_1 yellow_2)
		(on green_3 green_1)
		(on purple_1 green_3)
		(clear purple_1)

		(ontable blue_1)
		(on orange_1 blue_1)
		(on purple_2 orange_1)
		(clear purple_2)

		(ontable red_3)
		(on blue_3 red_3)
		(on green_4 blue_3)
		(clear green_4)

		(ontable orange_2)
		(on red_1 orange_2)
		(on green_2 red_1)
		(clear green_2)

		(ontable purple_3)
		(on yellow_1 purple_3)
		(on yellow_3 yellow_1)
		(clear yellow_3)

		(ontable yellow_4)
		(on blue_2 yellow_4)
		(on orange_3 blue_2)
		(on red_2 orange_3)
		(clear red_2)
	)
	(:goal (and (handempty robot)
		(ontable yellow_2)
		(on orange_1 yellow_2)
		(on yellow_1 orange_1)
		(on red_2 yellow_1)
		(clear red_2)

		(ontable green_1)
		(on orange_3 green_1)
		(on blue_2 orange_3)
		(clear blue_2)

		(ontable purple_3)
		(on red_1 purple_3)
		(on blue_3 red_1)
		(clear blue_3)

		(ontable yellow_4)
		(on green_3 yellow_4)
		(on red_3 green_3)
		(clear red_3)

		(ontable green_4)
		(on purple_2 green_4)
		(on green_2 purple_2)
		(clear green_2)

		(ontable orange_2)
		(on blue_1 orange_2)
		(on yellow_3 blue_1)
		(on purple_1 yellow_3)
		(clear purple_1)
	))
)