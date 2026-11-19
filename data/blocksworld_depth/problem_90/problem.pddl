(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue - block
		green - block
		orange - block
		purple - block
		red - block
		yellow - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable orange)
		(clear orange)
		(ontable yellow)
		(on green yellow)
		(clear green)

		(ontable blue)
		(on purple blue)
		(on red purple)
		(clear red)
	)
	(:goal (and (handempty robot)
		(ontable red)
		(clear red)
		(ontable green)
		(clear green)
		(ontable orange)
		(on yellow orange)
		(clear yellow)

		(ontable purple)
		(on blue purple)
		(clear blue)
	))
)